import type { Register } from 'claude-code'

/**
 * Auto-logs every prompt in this session into the genai-bank-governance
 * use-case register, the way the thesis's own "enterprise AI gateway"
 * framing says a real usage log would have to work: nobody fills in a
 * form, the gateway itself reads what the employee typed and classifies
 * it against the thesis's five dimensions.
 *
 * Two stages, deliberately kept apart:
 *  - `prompt.submit` is cheap and synchronous-feeling: it just appends the
 *    raw prompt to the shared log file as "pending" and lets the prompt go
 *    on its way immediately, so this mod never adds latency to a turn.
 *  - A `session.start` timer scans that file every SCAN_INTERVAL_MS, finds
 *    anything still "pending", classifies it with one model call per entry
 *    (mirroring classifier.py's prompt and validation rules exactly, so
 *    the thesis's dimensions mean the same thing here as they do there),
 *    and writes the result back in place.
 *
 * app.py reads this same file (LOG_PATH) and merges classified entries
 * into the Register tab, so nothing else needs to run for them to show up
 * there, just a page refresh.
 */

// Relative to $.fs's working directory, not a hardcoded absolute path: an
// absolute path baked in here would only be valid on the one machine this
// was written on. This resolves correctly for anyone running Claude Code
// with a clone of genai-bank-governance as their working directory, which
// is how app.py and auto_log.py already expect to find this file.
const LOG_PATH = 'data/auto_log.jsonl'
const SCAN_INTERVAL_MS = 20_000
const CLASSIFIER_MODEL = 'haiku'
const MAX_TEXT_CHARS = 1500
// A "failed" entry (bad JSON, a dropped request) is retried this many
// times on later scan ticks before being left alone for good, so one
// flaky model response doesn't permanently lose that prompt's entry.
const MAX_CLASSIFY_ATTEMPTS = 3
// The log file is read and rewritten in full on every scan tick and every
// prompt, so letting it grow forever over a long-running session would make
// both operations slower every time, not just use more disk. Once the
// classified/failed backlog passes this count, the oldest entries in that
// backlog are dropped first, never a "pending" one, since that would lose
// a classification that hasn't happened yet.
const MAX_LOG_ENTRIES = 2000

type Entry = {
  id: string
  text: string
  name: string
  status: 'pending' | 'classified' | 'failed'
  loggedAt: string
  classifiedAt?: string
  source: 'claude-code-auto'
  // True when `text` is the truncated head of a longer prompt (see
  // MAX_TEXT_CHARS / buildPrompt below). Kept on the entry, not just in the
  // prompt sent to the model, so the log itself is honest about the fact
  // that the classification ran on partial information.
  truncated?: boolean
  attempts?: number
  form?: string
  tool_access?: string
  information_involved?: string
  role_of_output?: string
  banking_process?: string
  task_expertise?: string
  rationale?: string
  error?: string
}

// Mirrors data/framework.py. Duplicated here (not imported) because this
// module runs in its own sandboxed environment with no access to the
// Python project's files; keep the two in sync by hand if the thesis's
// framework table in framework.py ever changes.
const FORMS_OF_USE = [
  {
    id: 'communication',
    name: 'Communication and content creation',
    description: 'Drafting or revising material for colleagues, customers or other recipients.',
  },
  {
    id: 'document_processing',
    name: 'Document and knowledge processing',
    description: 'Summarizing, extracting or retrieving information from existing material.',
  },
  {
    id: 'analytical',
    name: 'Analytical and decision-support activities',
    description: 'Interpreting information or supporting an assessment or recommendation.',
  },
  {
    id: 'technical',
    name: 'Technical assistance',
    description: 'Developing, modifying or maintaining internal software and systems.',
  },
] as const

const DIMENSIONS = [
  {
    id: 'tool_access',
    name: 'Tool and access arrangement',
    question: 'Which generative AI tool is used, and how does the employee access it?',
    options: [
      'Public service, not approved for this task',
      'Public service, approved for this task',
      'Enterprise tool',
      'Internal application connected to bank systems',
    ],
  },
  {
    id: 'information_involved',
    name: 'Information involved',
    question: 'What information is entered, retrieved or made accessible to the tool?',
    options: [
      'Public information',
      'Internal, non-sensitive information',
      'Confidential or proprietary information',
      'Personal or client data',
    ],
  },
  {
    id: 'role_of_output',
    name: 'Role of the output',
    question: "How is the generated output used in the employee's work?",
    options: [
      'Initial draft, reviewed and revised by the employee',
      'Recommendation used to support a decision',
      'Content used with limited or no review',
      'Generated code deployed to an internal system',
    ],
  },
  {
    id: 'banking_process',
    name: 'Banking process supported',
    question: 'In which banking process is the activity performed?',
    options: [
      'Internal administrative process',
      'Process involving customers',
      'Process involving compliance or regulation',
    ],
  },
  {
    id: 'task_expertise',
    name: 'Task and employee expertise',
    question: "What is the nature of the task, and can the employee independently evaluate the output?",
    options: [
      "Routine, within the employee's expertise",
      'Non-routine or specialist, within expertise',
      "Outside the employee's expertise",
    ],
  },
] as const

function buildPrompt(text: string, truncated: boolean): string {
  const formsBlock = FORMS_OF_USE.map(f => `- ${f.id}: ${f.name} (${f.description})`).join('\n')
  const dimsBlock = DIMENSIONS.map(
    d => `${d.id} (${d.name}): ${d.question}\nAllowed values: ${d.options.join(' | ')}`,
  ).join('\n\n')
  const truncationNote = truncated
    ? '\n\nNote: the text below was cut off at a length limit, so it may be ' +
      "missing its ending. Treat anything you can't determine because of " +
      'that as unknown and apply the conservative-default instruction below.'
    : ''

  return `You are classifying a short, plain-language description of something a bank
employee did with a generative AI tool, against a fixed set of categories.

Forms of use (pick exactly one id):
${formsBlock}

Dimensions (pick exactly one of the allowed values for each, copied verbatim):
${dimsBlock}

Note on banking_process specifically: the test is whether the output feeds
into or affects an actual compliance, regulatory, customer, or regulated-
system outcome (a regulatory filing, an AML case, a credit committee
decision, code deployed to a regulated financial system such as payments,
a customer's account or interaction) rather than whether the subject matter
merely sounds regulated. Reading or summarizing public information about a
regulated topic for one's own general awareness, with no operational effect
on any actual decision, system or customer, is "Internal administrative
process," even when the topic itself (a new regulation, a rate decision) is
regulatory in nature. The topic of the content is not the same as the
process the employee's work actually affects.

Employee's description of what they did:
"""${text.slice(0, MAX_TEXT_CHARS)}"""${truncationNote}

Classify this use case. Use only information stated or clearly implied by the
description. If a dimension cannot be determined from the description, pick
the most conservative (highest-risk) plausible value rather than guessing low,
since under-classifying risk is worse than over-classifying it. This
conservative default does not override the banking_process note above: a
genuinely internal, non-regulatory, non-customer-facing task stays "Internal
administrative process" even under conservative defaulting.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{
  "form": "<one form id>",
  "tool_access": "<one allowed value>",
  "information_involved": "<one allowed value>",
  "role_of_output": "<one allowed value>",
  "banking_process": "<one allowed value>",
  "task_expertise": "<one allowed value>",
  "rationale": "<one sentence on why you picked these>"
}`
}

function isValidClassification(parsed: any): boolean {
  if (typeof parsed !== 'object' || parsed === null) return false
  if (!FORMS_OF_USE.some(f => f.id === parsed.form)) return false
  return DIMENSIONS.every(d => d.options.includes(parsed[d.id]))
}

// Mirrors classifier.py's _extract_json_object(): scans for the first
// balanced {...} block rather than just stripping a code fence, since not
// every provider is equally disciplined about returning bare JSON
// (GPT-4o-mini sometimes adds a trailing sentence after the closing brace,
// which a simple fence-strip doesn't handle).
function extractJsonObject(raw: string): string {
  const start = raw.indexOf('{')
  if (start === -1) return raw.trim()

  let depth = 0
  let inString = false
  let escape = false
  for (let i = start; i < raw.length; i++) {
    const ch = raw[i]
    if (inString) {
      if (escape) escape = false
      else if (ch === '\\') escape = true
      else if (ch === '"') inString = false
      continue
    }
    if (ch === '"') inString = true
    else if (ch === '{') depth += 1
    else if (ch === '}') {
      depth -= 1
      if (depth === 0) return raw.slice(start, i + 1)
    }
  }
  return raw.slice(start)
}

function parseModelJson(raw: string): any {
  return JSON.parse(extractJsonObject(raw.trim()))
}

async function readLog($: any): Promise<Entry[]> {
  const exists = await $.fs.exists(LOG_PATH)
  if (!exists) return []
  const text = await $.fs.read(LOG_PATH)
  return text
    .split('\n')
    .map((line: string) => line.trim())
    .filter(Boolean)
    .map((line: string) => JSON.parse(line))
}

async function writeLog($: any, entries: Entry[]): Promise<void> {
  const text = entries.map(e => JSON.stringify(e)).join('\n') + (entries.length ? '\n' : '')
  await $.fs.write(LOG_PATH, text)
}

// prompt.submit (adding one new "pending" entry) and the session.start
// timer (rewriting a batch of entries it just classified) both read-modify-
// write the same file with no locking. Without this, a write finishing
// after a slower one can silently erase it: the timer reads the file,
// spends a few seconds classifying, a new prompt is submitted and written
// in that gap, then the timer's own write goes out based on its stale
// read and wipes out that new entry.
//
// mergeAndWrite closes that gap by re-reading the file immediately before
// writing and folding in anything that showed up there since the caller's
// own read, keyed by id (the caller's version of a given id wins, since it
// reflects more recent state for that entry).
async function mergeAndWrite($: any, updated: Entry[]): Promise<void> {
  let onDisk: Entry[] = []
  try {
    onDisk = await readLog($)
  } catch {
    onDisk = []
  }
  const byId = new Map<string, Entry>()
  for (const e of onDisk) byId.set(e.id, e)
  for (const e of updated) byId.set(e.id, e)
  await writeLog($, trimLog(Array.from(byId.values())))
}

// Keeps the file from growing without bound over a long-running session.
// "pending" entries are always kept, however many there are, since dropping
// one would lose a prompt before it was ever classified; if the backlog of
// already-resolved (classified/failed) entries exceeds MAX_LOG_ENTRIES, the
// oldest of those are dropped first, oldest-logged first.
function trimLog(entries: Entry[]): Entry[] {
  const pending = entries.filter(e => e.status === 'pending')
  const resolved = entries
    .filter(e => e.status !== 'pending')
    .sort((a, b) => a.loggedAt.localeCompare(b.loggedAt))

  const overflow = resolved.length - MAX_LOG_ENTRIES
  const keptResolved = overflow > 0 ? resolved.slice(overflow) : resolved
  return [...keptResolved, ...pending]
}

export const register: Register = on => {
  // Stage 1: capture every genuine prompt, cheaply, and let it through at once.
  // Wrapped so that logging can never deny or delay the actual prompt: the
  // try/catch covers every call this hook makes, and the registration's own
  // .catch is a second line of defense that always lets the prompt through
  // even if something fails before the try block is reached.
  on('prompt.submit', async ($, e, next) => {
    try {
      const text = e.text.trim()
      if (!e.isMeta && !e.command && text.length > 0) {
        // Only the one new entry is written here (via mergeAndWrite, not a
        // full read-modify-write of the whole file) so this can never clobber
        // a concurrent write from the session.start scan timer below.
        await mergeAndWrite($, [
          {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            text,
            name: text.length > 80 ? `${text.slice(0, 80)}…` : text,
            status: 'pending',
            loggedAt: new Date().toISOString(),
            source: 'claude-code-auto',
          },
        ])
      }
    } catch {
      // Logging must never block or break the person's actual prompt.
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  // Stage 2: a standing timer that scans for pending entries and classifies
  // them, independent of any one prompt's dispatch.
  on('session.start', async ($, e, next) => {
    $.clock.every(SCAN_INTERVAL_MS, async () => {
      let entries: Entry[]
      try {
        entries = await readLog($)
      } catch {
        return
      }

      // Retry entries that failed before too (a dropped request, a model
      // reply that didn't parse), not just ones still "pending", but only
      // up to MAX_CLASSIFY_ATTEMPTS, so a response that will never validate
      // (not a transient hiccup) doesn't get retried forever.
      const toClassify = entries.filter(
        x =>
          x.status === 'pending' ||
          (x.status === 'failed' && (x.attempts ?? 1) < MAX_CLASSIFY_ATTEMPTS),
      )
      if (toClassify.length === 0) return

      let classifiedCount = 0
      const processed: Entry[] = []
      for (const entry of toClassify) {
        entry.attempts = (entry.attempts ?? 0) + 1
        entry.truncated = entry.text.length > MAX_TEXT_CHARS

        const result = await $.model.complete({
          model: CLASSIFIER_MODEL,
          prompt: buildPrompt(entry.text, entry.truncated),
          maxTokens: 400,
        })

        if (!result.isAnswered) {
          entry.status = 'failed'
          entry.error = result.reason
          processed.push(entry)
          continue
        }

        try {
          const parsed = parseModelJson(result.text)
          if (!isValidClassification(parsed)) {
            throw new Error('model returned an unrecognized classification value')
          }
          entry.status = 'classified'
          entry.classifiedAt = new Date().toISOString()
          entry.form = parsed.form
          entry.tool_access = parsed.tool_access
          entry.information_involved = parsed.information_involved
          entry.role_of_output = parsed.role_of_output
          entry.banking_process = parsed.banking_process
          entry.task_expertise = parsed.task_expertise
          entry.rationale = parsed.rationale
          classifiedCount += 1
        } catch (err) {
          entry.status = 'failed'
          entry.error = String(err)
        }
        processed.push(entry)
      }

      try {
        // Only the entries this tick actually touched are merged in, so a
        // prompt.submit that landed mid-scan isn't lost (see mergeAndWrite).
        await mergeAndWrite($, processed)
      } catch {
        // If the write fails, these entries' attempts increments are lost
        // too, but their in-file status is still whatever it was before
        // this tick, so the next tick retries them rather than losing them.
        return
      }

      if (classifiedCount > 0) {
        $.ui.toast(
          `GenAI usage log: classified ${classifiedCount} prompt${classifiedCount === 1 ? '' : 's'} into the register.`,
        )
      }
    })

    return next(e)
  })
}
