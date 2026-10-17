const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const base = path.join(__dirname, '../overlay/assets/extensions/acute-midnight');

function panel(options = {}) {
  const nodes = {};
  const node = (id) => nodes[id] ||= { disabled: true, hidden: true, checked: false,
    textContent: '', listeners: {}, addEventListener(name, handler) { this.listeners[name] = handler; } };
  const modes = ['off', 'automatic', 'always'].map(value => Object.assign(node(value), { value }));
  const writes = [], reloads = [];
  const context = {
    URL,
    document: {
      getElementById: node,
      querySelector: () => node('fieldset'),
      querySelectorAll: () => modes,
    },
    browser: {
      extension: { inIncognitoContext: !!options.privateContext },
      tabs: {
        query: async () => [{ id: 7, url: 'https://example.com/path', incognito: !!options.privateTab }],
        reload: async id => { reloads.push(id); if (options.reloadFailure) throw Error('reload'); },
      },
      storage: { local: {
        get: options.get || (async () => options.storage || {}),
        set: async values => { writes.push(values); if (options.set) await options.set(values); },
      } },
    },
  };
  const ready = vm.runInNewContext(fs.readFileSync(path.join(base, 'popup.js'), 'utf8'), context);
  return { ready, nodes, modes, writes, reloads };
}

test('popup blocks writes until storage has loaded', async () => {
  let release;
  const p = panel({ get: () => new Promise(resolve => { release = resolve; }) });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(p.nodes.fieldset.disabled, true);
  assert.equal(p.modes[0].listeners.change, undefined);
  release({});
  await p.ready;
  assert.equal(p.nodes.fieldset.disabled, false);
});

test('private tabs and private extension contexts never load settings or expose a hostname', async () => {
  for (const flags of [{ privateTab: true }, { privateContext: true }]) {
    let reads = 0;
    const p = panel({ ...flags, get: async () => { reads++; return {}; } });
    await p.ready;
    assert.equal(reads, 0);
    assert.equal(p.nodes.fieldset.disabled, true);
    assert.match(p.nodes.status.textContent, /private/);
    assert.equal(p.nodes['site-name'], undefined);
  }
});

test('failed load leaves every mutation disabled', async () => {
  const p = panel({ get: async () => { throw Error('read'); } });
  await p.ready;
  assert.equal(p.nodes.fieldset.disabled, true);
  assert.match(p.nodes.status.textContent, /could not be loaded/);
});

test('failed save restores the saved mode and does not reload', async () => {
  const p = panel({ set: async () => { throw Error('write'); } });
  await p.ready;
  await p.modes[2].listeners.change();
  assert.equal(p.modes[1].checked, true);
  assert.deepEqual(p.reloads, []);
  assert.match(p.nodes.status.textContent, /could not be saved/);
});

test('failed site save preserves the previous disabled-host set for the next attempt', async () => {
  let fail = true;
  const p = panel({ set: async () => { if (fail) throw Error('write'); } });
  await p.ready;
  p.nodes['site-enabled'].checked = false;
  await p.nodes['site-enabled'].listeners.change();
  assert.equal(p.nodes['site-enabled'].checked, true);
  fail = false;
  p.nodes['site-enabled'].checked = false;
  await p.nodes['site-enabled'].listeners.change();
  assert.deepEqual(Array.from(p.writes[1].disabledHosts), ['example.com']);
  assert.deepEqual(p.reloads, [7]);
});

test('repeated changes cannot race storage writes', async () => {
  let finish;
  const p = panel({ set: () => new Promise(resolve => { finish = resolve; }) });
  await p.ready;
  const first = p.modes[2].listeners.change();
  await p.modes[0].listeners.change();
  assert.equal(p.writes.length, 1);
  finish();
  await first;
  assert.equal(p.modes[2].checked, true);
});

test('malformed local settings fall back safely and reload errors retain saved values', async () => {
  const p = panel({ storage: { mode: '<invalid>', disabledHosts: 42 }, reloadFailure: true });
  await p.ready;
  assert.equal(p.modes[1].checked, true);
  await p.modes[2].listeners.change();
  assert.equal(p.modes[2].checked, true);
  assert.match(p.nodes.status.textContent, /Settings saved/);
});

test('content script ignores storage failures and private pages', async () => {
  const code = fs.readFileSync(path.join(base, 'midnight.js'), 'utf8');
  for (const privatePage of [false, true]) {
    let reads = 0;
    await vm.runInNewContext(code, {
      browser: { extension: { inIncognitoContext: privatePage }, storage: { local: {
        get: async () => { reads++; throw Error('read'); },
      } } },
      location: { protocol: 'https:', hostname: 'example.com', pathname: '/' },
      document: { contentType: 'text/html' },
    });
    assert.equal(reads, privatePage ? 0 : 1);
  }
});
