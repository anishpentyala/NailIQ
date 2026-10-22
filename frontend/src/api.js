import axios from 'axios'
import { visibleFindings } from './conditions'

// On localhost the backend is on :5000. Opened from any other host (an HTTPS tunnel for phone testing), use the same
// origin: the Vite dev server proxies the API paths to the backend (see vite.config.js).
const onLocalhost = ['localhost', '127.0.0.1', '[::1]', '::1'].includes(window.location.hostname)
const API_BASE = import.meta.env.VITE_API_BASE || (onLocalhost ? 'http://localhost:5000' : '')

export async function analyzeImages({ sideImage, topImage, topNailBbox }) {
  const res = await axios.post(`${API_BASE}/analyze`, {
    side_image: sideImage,
    top_image: topImage,
    ...(topNailBbox ? { top_nail_bbox: topNailBbox } : {}),
  })
  return { ...res.data, findings: visibleFindings(res.data.findings) }
}

export async function validatePhoto(base64Image, view, topNailBbox) {
  const res = await axios.post(`${API_BASE}/validate_photo`, {
    image: base64Image,
    view,
    ...(topNailBbox ? { top_nail_bbox: topNailBbox } : {}),
  })
  return res.data
}

export async function getHistory(limit) {
  const res = await axios.get(`${API_BASE}/history`, { params: limit ? { limit } : undefined })
  const data = res.data
  return { ...data, scans: (data.scans ?? []).map((scan) => ({ ...scan, findings: visibleFindings(scan.findings) })) }
}

export async function submitFeedback({ scanId, label, shownVerdict, agreed, note }) {
  const res = await axios.post(`${API_BASE}/feedback`, {
    scan_id: scanId ?? null,
    label,
    shown_verdict: shownVerdict,
    agreed,
    note: note ?? null,
  })
  return res.data
}
