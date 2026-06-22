import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

export async function analyzeImage(base64Image) {
  const res = await axios.post(`${API_BASE}/analyze`, { image: base64Image })
  return res.data
}
