// Client for the on-device AI: a web worker (public/ondevice-worker.js) that runs the analysis code and the neural
// networks inside this browser, so photos are never uploaded. Falls back to the server API when the bundle is not
// installed or the browser cannot run it (see api.js).

let worker = null
let nextId = 1
const calls = new Map()
let initPromise = null
let bundlePromise = null
let state = { phase: 'idle', done: 0, total: 0 } // idle | downloading | starting | ready | unavailable
const listeners = new Set()

function setState(next) {
  state = { ...state, ...next }
  listeners.forEach((fn) => fn(state))
}

export const getOnDeviceState = () => state

export function subscribeOnDevice(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

// true when the on-device bundle (scripts/build_ondevice.py) is being served next to the app
export function bundlePresent() {
  if (!bundlePromise) {
    bundlePromise = (async () => {
      try {
        const res = await fetch('/ondevice/manifest.json', { cache: 'no-cache' })
        if (!res.ok) return false
        const manifest = await res.json() // a dev server answers missing files with index.html, which is not JSON
        return Array.isArray(manifest.models)
      } catch {
        return false
      }
    })()
  }
  return bundlePromise
}

function post(type, payload) {
  return new Promise((resolve, reject) => {
    const id = nextId++
    calls.set(id, { resolve, reject })
    worker.postMessage({ id, type, payload })
  })
}

export function startOnDevice() {
  if (initPromise) return initPromise
  initPromise = (async () => {
    const capable = typeof Worker !== 'undefined' && typeof WebAssembly === 'object' && 'caches' in window
    if (!capable || !(await bundlePresent())) {
      setState({ phase: 'unavailable' })
      return false
    }
    try {
      worker = new Worker('/ondevice-worker.js')
      worker.onmessage = ({ data }) => {
        if (data.progress) {
          setState({ phase: data.progress.done >= data.progress.total ? 'starting' : 'downloading', ...data.progress })
          return
        }
        const call = calls.get(data.id)
        if (!call) return
        calls.delete(data.id)
        if (data.ok) call.resolve(data.result)
        else call.reject(new Error(data.error))
      }
      worker.onerror = (e) => console.warn('on-device worker error', e.message)
      setState({ phase: 'downloading' })
      await post('init')
      setState({ phase: 'ready' })
      return true
    } catch (err) {
      console.warn('on-device AI unavailable, using the server instead:', err)
      setState({ phase: 'unavailable' })
      return false
    }
  })()
  return initPromise
}

export async function onDeviceReady() {
  return (await startOnDevice()) === true
}

export async function onDeviceCall(type, payload) {
  const { status, body } = await post(type, payload)
  if (status !== 200) {
    const error = new Error(body?.error ?? 'on-device analysis failed')
    error.response = { status, data: body }
    throw error
  }
  return body
}

// same as onDeviceCall but returns the raw worker answer including timing, for diagnostics
export const onDeviceCallRaw = (type, payload) => post(type, payload)
