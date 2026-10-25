import axios from 'axios'
import { visibleFindings } from './conditions'
import { bundlePresent, onDeviceCall, onDeviceReady } from './ondevice'
import { clearLocalScans, listLocalScans, saveLocalFeedback, saveLocalScan } from './localHistory'

// On localhost the backend is on :5000. Opened from any other host (an HTTPS tunnel for phone testing), use the same
// origin: the Vite dev server proxies the API paths to the backend (see vite.config.js).
const onLocalhost = ['localhost', '127.0.0.1', '[::1]', '::1'].includes(window.location.hostname)
const API_BASE = import.meta.env.VITE_API_BASE || (onLocalhost ? 'http://localhost:5000' : '')

// Anonymous per-browser id so a shared server shows each person only their own History. Not an account; no personal data.
function clientId() {
  try {
    let id = localStorage.getItem('nailiq.clientId')
    if (!id) {
      id = (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`).replace(/[^A-Za-z0-9_-]/g, '')
      localStorage.setItem('nailiq.clientId', id)
    }
    return id
  } catch {
    return null // storage blocked: History simply is not separated
  }
}
axios.interceptors.request.use((config) => {
  const id = clientId()
  if (id) config.headers['X-Client-Id'] = id
  return config
})

// When the on-device AI bundle is installed, scans, History and feedback all stay on this device. Otherwise the same
// calls go to the server.
export async function analyzeImages({ sideImage, topImage, topNailBbox }) {
  const payload = {
    side_image: sideImage,
    top_image: topImage,
    ...(topNailBbox ? { top_nail_bbox: topNailBbox } : {}),
  }
  const local = await bundlePresent()
  let data
  if (local && (await onDeviceReady())) {
    data = await onDeviceCall('analyze', payload)
  } else {
    data = (await axios.post(`${API_BASE}/analyze`, payload)).data
  }
  const scanId = local ? saveLocalScan(data.findings).id : data.scan_id
  return { ...data, scan_id: scanId, findings: visibleFindings(data.findings) }
}

export async function validatePhoto(base64Image, view, topNailBbox) {
  const payload = { image: base64Image, view, ...(topNailBbox ? { top_nail_bbox: topNailBbox } : {}) }
  if ((await bundlePresent()) && (await onDeviceReady())) return onDeviceCall('validate', payload)
  return (await axios.post(`${API_BASE}/validate_photo`, payload)).data
}

export async function getHistory(limit) {
  let data
  if (await bundlePresent()) data = { scans: listLocalScans(limit) }
  else data = (await axios.get(`${API_BASE}/history`, { params: limit ? { limit } : undefined })).data
  return { ...data, scans: (data.scans ?? []).map((scan) => ({ ...scan, findings: visibleFindings(scan.findings) })) }
}

export async function submitFeedback({ scanId, label, shownVerdict, agreed, note }) {
  if (await bundlePresent()) {
    saveLocalFeedback({ scan_id: scanId ?? null, label, shown_verdict: shownVerdict, agreed, note: note ?? null })
    return { ok: true }
  }
  const res = await axios.post(`${API_BASE}/feedback`, {
    scan_id: scanId ?? null,
    label,
    shown_verdict: shownVerdict,
    agreed,
    note: note ?? null,
  })
  return res.data
}

export async function clearHistory() {
  if (await bundlePresent()) {
    clearLocalScans()
    return { deleted: 0 }
  }
  const res = await axios.delete(`${API_BASE}/history`)
  return res.data
}
