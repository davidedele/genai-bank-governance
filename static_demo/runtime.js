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
    status.textContent = failed ? text : text + ' You can look around meanwhile. Answering, saving and exporting start when this finishes.';
    status.classList.toggle('failed', !!failed);
  }

  // Python takes a while to download on the first visit. The page does not wait for it:
  // the start-up data was made by the real app at build time and is shown straight away,
  // and everything that needs Python waits until it is ready. Downloads run side by side.
  const PACKAGES = ['fastapi', 'pydantic', 'sqlite3'];
  const getText = async (path) => {
    const reply = await realFetch(cfg.pyBase + path);
    if (!reply.ok) throw new Error('Could not download ' + path + '.');
    return reply.text();
  };
  const startUp = getText('bootstrap.json').then(JSON.parse).catch(() => null);
  let token = '';

  const ready = (async () => {
    say('Step 1 of 3: downloading Python. The first visit can take up to half a minute.');
    const manifest = JSON.parse(await getText('manifest.json'));
    const sources = Promise.all(manifest.files.concat('bridge.py').map(async (file) => [file, await getText(file)]));
    sources.catch(() => {});
    await new Promise((ok, fail) => {
      const s = document.createElement('script');
      s.src = cfg.pyodideUrl + 'pyodide.js';
      s.onload = ok;
      s.onerror = () => fail(new Error('Could not download the Python runtime.'));
      document.head.append(s);
    });
    const py = await window.loadPyodide({ indexURL: cfg.pyodideUrl });
    say('Step 2 of 3: loading the app libraries.');
    await py.loadPackage(PACKAGES);
    say('Step 3 of 3: starting the app.');
    for (const [file, text] of await sources) {
      const dir = file.includes('/') ? file.slice(0, file.lastIndexOf('/')) : '';
      const target = file === 'bridge.py' ? '/home/pyodide' : '/home/pyodide/app' + (dir ? '/' + dir : '');
      py.FS.mkdirTree(target);
      py.FS.writeFile(file === 'bridge.py' ? '/home/pyodide/bridge.py' : '/home/pyodide/app/' + file, text);
    }
    py.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
    bridge = py.pyimport('bridge');
    token = JSON.parse(JSON.parse(await bridge.request('GET', '/api/bootstrap', '', '')).body).token;
    if (status) status.hidden = true;
  })().catch((e) => {
    say('The demo could not start: ' + e.message + ' Reload the page, or run the project on your own computer.', true);
    throw e;
  });
  ready.catch(() => {});

  window.fetch = async function (input, init) {
    // Only the page's own calls such as fetch('/api/...') are answered here. Anything else, including Pyodide's downloads, goes through.
    const url = typeof input === 'string' ? input : '';
    if (!url.startsWith('/api/')) return realFetch(input, init);
    const options = init || {};
    if (url === '/api/bootstrap') {
      const data = await startUp;
      if (data) return new Response(JSON.stringify(Object.assign({ token: 'starting' }, data)), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    await ready;
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
