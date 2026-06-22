import { useState, useCallback } from 'react'
import CameraCapture from './components/CameraCapture'
import ResultView from './components/ResultView'
import { analyzeImage } from './api'
import './App.css'

function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleCapture = useCallback(async (base64Image) => {
    setLoading(true)
    setError(null)
    try {
      const data = await analyzeImage(base64Image)
      setResult(data)
    } catch (err) {
      setError("Couldn't reach the analysis server. Is the backend running?")
    } finally {
      setLoading(false)
    }
  }, [])

  const handleReset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="brand">Lovibond</h1>
        <p className="tagline">A precautionary nail-angle screener</p>
      </header>

      <p className="disclaimer-banner">
        This is an educational screening tool, not a diagnosis. It only flags whether
        your nail angle is typical or worth a doctor's look.
      </p>

      {error && <div className="camera-error">{error}</div>}

      {result ? (
        <ResultView result={result} onReset={handleReset} />
      ) : (
        <CameraCapture onCapture={handleCapture} loading={loading} />
      )}
    </div>
  )
}

export default App
