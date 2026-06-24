import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

export async function analyzeImages({ sideImage, topImage }) {
  const res = await axios.post(`${API_BASE}/analyze`, {
    side_image: sideImage,
    top_image: topImage,
  })
  return res.data
}

export async function validatePhoto(base64Image, view) {
  const res = await axios.post(`${API_BASE}/validate_photo`, {
    image: base64Image,
    view,
  })
  return res.data
}

export async function getHistory() {
  const res = await axios.get(`${API_BASE}/history`)
  return res.data
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
