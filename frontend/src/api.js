import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

export async function analyzeImages({ sideImage, topImage, topNailBbox }) {
  const res = await axios.post(`${API_BASE}/analyze`, {
    side_image: sideImage,
    top_image: topImage,
    ...(topNailBbox ? { top_nail_bbox: topNailBbox } : {}),
  })
  return res.data
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
