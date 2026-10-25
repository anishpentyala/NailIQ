/* global importScripts */
/* NailIQ on-device AI worker (classic worker so importScripts works).
 *
 * Runs the same Python analysis code the server uses (ml/infer, via Pyodide = Python compiled to WebAssembly) and the
 * neural networks (ONNX, via onnxruntime-web) entirely inside this browser. Photos are never uploaded.
 * Everything it loads comes from /ondevice/ (built by scripts/build_ondevice.py) and is kept in the browser's Cache
 * Storage, so after the first download it starts without any network.
 *
 * Messages in:  {id, type: 'init' | 'analyze' | 'validate', payload}
 * Messages out: {id, ok, result | error}   and   {progress: {done, total}}   while downloading.
 */
const BASE = '/ondevice/'
let manifest = null
let pyodide = null
let api = null
let doneBytes = 0
let totalBytes = 0
let queue = Promise.resolve()

const realFetch = self.fetch.bind(self)
const cacheName = () => `nailiq-ondevice-${manifest ? manifest.version : 'boot'}`

// Cache-first for everything under /ondevice/ (Pyodide and onnxruntime fetch their own wasm/wheels through this too).
self.fetch = async (input, init) => {
  const url = new URL(typeof input === 'string' ? input : input.url, self.location.href)
  if (!url.pathname.startsWith(BASE) || url.pathname === BASE + 'manifest.json' || !manifest) return realFetch(input, init)
  const cache = await caches.open(cacheName())
  const hit = await cache.match(url.pathname)
  if (hit) return hit
  const res = await realFetch(url.pathname)
  if (!res.ok) return res
  await cache.put(url.pathname, res.clone())
  const size = manifest.files[url.pathname.slice(BASE.length)] || 0
  doneBytes += size
  self.postMessage({ progress: { done: Math.min(doneBytes, totalBytes), total: totalBytes } })
  return res
}

async function prefetchAll() {
  const cache = await caches.open(cacheName())
  const missing = []
  for (const [path, size] of Object.entries(manifest.files)) {
    if (!(await cache.match(BASE + path))) missing.push([path, size])
    else doneBytes += size
  }
  totalBytes = Object.values(manifest.files).reduce((a, b) => a + b, 0)
  self.postMessage({ progress: { done: doneBytes, total: totalBytes } })
  // 4 at a time: the big model files dominate, so more connections add little
  let next = 0
  const lane = async () => {
    while (next < missing.length) {
      const [path] = missing[next++]
      await self.fetch(BASE + path)
    }
  }
  await Promise.all([lane(), lane(), lane(), lane()])
  // drop caches from older builds
  for (const key of await caches.keys()) if (key.startsWith('nailiq-ondevice-') && key !== cacheName()) await caches.delete(key)
}

async function init() {
  const res = await realFetch(BASE + 'manifest.json', { cache: 'no-cache' })
  if (!res.ok) throw new Error('on-device bundle not installed')
  manifest = await res.json()
  await prefetchAll()

  importScripts(BASE + 'ort/ort.wasm.min.js')
  self.ort.env.wasm.wasmPaths = BASE + 'ort/'
  self.ort.env.wasm.numThreads = 1 // multi-threading measured no faster here and needs cross-origin isolation
  self.ort.env.wasm.proxy = false

  importScripts(BASE + 'pyodide/pyodide.js')
  pyodide = await self.loadPyodide({ indexURL: BASE + 'pyodide/' })
  await pyodide.loadPackage(manifest.packages)
  const zip = await (await self.fetch(BASE + 'py/ml_bundle.zip')).arrayBuffer()
  pyodide.unpackArchive(zip, 'zip', { extractDir: '/app' })
  pyodide.runPython("import sys\nif '/app' not in sys.path: sys.path.insert(0, '/app')")
  api = pyodide.pyimport('ml.infer.ondevice_api')
  const names = pyodide.toPy(manifest.models)
  api.configure(names)
  names.destroy()
}

// run the recorded network calls (grouped per network so each is loaded once), return their outputs to Python
async function runNetworks(requests, nets) {
  const byModel = new Map()
  for (const r of requests) {
    if (!byModel.has(r.name)) byModel.set(r.name, [])
    byModel.get(r.name).push(r)
  }
  for (const [name, list] of byModel) {
    const tc = performance.now()
    const bytes = await (await self.fetch(BASE + 'models/' + name)).arrayBuffer()
    const session = await self.ort.InferenceSession.create(new Uint8Array(bytes), { executionProviders: ['wasm'], graphOptimizationLevel: 'all' })
    const created = performance.now() - tc
    const tr = performance.now()
    try {
      for (const r of list) {
        const input = new self.ort.Tensor('float32', r.data, r.shape)
        const out = (await session.run({ input })).logits
        const logits = new Float32Array(out.data)
        api.provide(r.key, new Uint8Array(logits.buffer), out.dims[1])
      }
    } finally {
      await session.release()
      if (nets) nets.push([name, Math.round(created), Math.round(performance.now() - tr), list.reduce((a, r) => a + r.shape[0], 0)])
    }
  }
}

async function runApi(fn, payload) {
  const json = JSON.stringify(payload)
  const timing = { python_ms: 0, network_ms: 0, passes: 0, nets: [] }
  try {
    for (let pass = 0; pass < 10; pass++) {
      const t0 = performance.now()
      const out = JSON.parse(api[fn](json))
      timing.python_ms += performance.now() - t0
      timing.passes++
      if (!out.needs_inference) return { status: out.status, body: out.body, timing }
      const proxy = api.pending()
      const rows = proxy.toJs()
      proxy.destroy()
      const requests = rows.map(([key, name, shape, raw]) => ({
        key, name, shape: Array.from(shape), data: new Float32Array(raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength)),
      }))
      const t1 = performance.now()
      await runNetworks(requests, timing.nets)
      timing.network_ms += performance.now() - t1
    }
    throw new Error('analysis did not converge')
  } finally {
    api.reset()
  }
}

self.onmessage = (e) => {
  const { id, type, payload } = e.data
  queue = queue.then(async () => {
    try {
      let result = true
      if (type === 'init') await init()
      else if (type === 'analyze') result = await runApi('analyze', payload)
      else if (type === 'validate') result = await runApi('validate_photo', payload)
      self.postMessage({ id, ok: true, result })
    } catch (err) {
      self.postMessage({ id, ok: false, error: String((err && err.message) || err) })
    }
  })
}
