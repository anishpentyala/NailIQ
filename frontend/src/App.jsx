import { useState, useCallback } from 'react'
import CameraCapture from './components/CameraCapture'
import ResultView from './components/ResultView'
import InfoSection from './components/InfoSection'
import BottomNav from './components/BottomNav'
import { analyzeImages } from './api'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('scan')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleCapture = useCallback(async ({ sideImage, topImage }) => {
    setLoading(true)
    setError(null)
    try {
      const data = await analyzeImages({ sideImage, topImage })
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
        <span className="brand-icon" aria-hidden="true">◐</span>
        <h1 className="brand">NailIQ</h1>
        <p className="tagline">A precautionary nail-health screener</p>
      </header>

      <p className="disclaimer-banner">
        <span aria-hidden="true">ⓘ</span> This is an educational screening tool, not a
        diagnosis. It only flags whether your nail signs are typical or worth a doctor's look.
      </p>

      {activeTab === 'scan' ? (
        <>
          {error && <div className="camera-error">{error}</div>}
          {result ? (
            <ResultView result={result} onReset={handleReset} />
          ) : (
            <CameraCapture onCapture={handleCapture} loading={loading} />
          )}
        </>
      ) : (
        <InfoSection />
      )}

      <BottomNav active={activeTab} onChange={setActiveTab} />
    </div>
  )
}

export default App
