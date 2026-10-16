/* Runs the real Python app inside the browser (Pyodide) and answers the page's /api requests.
   Nothing the visitor enters leaves the page. Loaded before app.js by the static demo build. */
(function () {
  const cfg = window.DEMO_CONFIG;
  const realFetch = window.fetch.bind(window);
  const status = document.getElementById('demo-loading');
  let bridge = null;

  function say(text, failed) {
    if (!status) return;
    status.hidden = false;
    status.textContent = text;
    status.classList.toggle('failed', !!failed);
  }

  const ready = (async () => {
    say('Loading the demo. The first visit takes up to half a minute, because Python is downloaded to your browser.');
    await new Promise((ok, fail) => {
      const s = document.createElement('script');
      s.src = cfg.pyodideUrl + 'pyodide.js';
      s.onload = ok;
      s.onerror = () => fail(new Error('Could not download the Python runtime.'));
      document.head.append(s);
    });
    const py = await window.loadPyodide({ indexURL: cfg.pyodideUrl });
    await py.loadPackage(['fastapi', 'pydantic', 'sqlite3']);
    const manifest = await (await realFetch(cfg.pyBase + 'manifest.json')).json();
    for (const file of manifest.files) {
      const dir = file.includes('/') ? file.slice(0, file.lastIndexOf('/')) : '';
      py.FS.mkdirTree('/home/pyodide/app' + (dir ? '/' + dir : ''));
      const text = await (await realFetch(cfg.pyBase + file)).text();
      py.FS.writeFile('/home/pyodide/app/' + file, text);
    }
    py.FS.writeFile('/home/pyodide/bridge.py', await (await realFetch(cfg.pyBase + 'bridge.py')).text());
    py.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
    bridge = py.pyimport('bridge');
    if (status) status.hidden = true;
  })().catch((e) => {
    say('The demo could not start: ' + e.message + ' Reload the page, or run the project on your own computer.', true);
    throw e;
  });

  window.fetch = async function (input, init) {
    // Only the page's own calls such as fetch('/api/...') are answered here. Anything else, including Pyodide's downloads, goes through.
    const url = typeof input === 'string' ? input : '';
    if (!url.startsWith('/api/')) return realFetch(input, init);
    await ready;
    const options = init || {};
    const headers = options.headers || {};
    const token = headers['X-Workspace-Token'] || headers['x-workspace-token'] || '';
    const reply = JSON.parse(await bridge.request((options.method || 'GET').toUpperCase(), url, options.body || '', token));
    return new Response(reply.body, {
      status: reply.status,
      headers: Object.assign({ 'Content-Type': reply.type || 'application/json' }, reply.disposition ? { 'Content-Disposition': reply.disposition } : {})
    });
  };

  // The export links are plain links, so turn a click into a download made in the page.
  document.addEventListener('click', async (event) => {
    const link = event.target.closest && event.target.closest('a[href^="/api/export/"]');
    if (!link) return;
    event.preventDefault();
    const reply = await window.fetch(link.getAttribute('href'));
    const blob = await reply.blob();
    const name = (reply.headers.get('Content-Disposition') || '').split('filename=')[1] || 'export';
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
})();
