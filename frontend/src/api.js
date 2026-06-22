import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

export async function analyzeImages({ sideImage, topImage }) {
  const res = await axios.post(`${API_BASE}/analyze`, {
    side_image: sideImage,
    top_image: topImage,
  })
  return res.data
}
