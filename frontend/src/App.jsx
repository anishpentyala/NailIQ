import { useState, useCallback } from 'react'
import CameraCapture from './components/CameraCapture'
import ResultView from './components/ResultView'
import InfoSection from './components/InfoSection'
import HomeScreen from './components/HomeScreen'
import BottomNav from './components/BottomNav'
import Icon from './components/Icon'
import { analyzeImages } from './api'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('home')
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

  const startScan = useCallback(() => {
    setResult(null)
    setError(null)
    setActiveTab('scan')
  }, [])

  const closeScan = useCallback(() => {
    setResult(null)
    setError(null)
    setActiveTab('home')
  }, [])

  // When camera is actively showing (scan tab, no result yet), go full-screen
  const isCameraActive = activeTab === 'scan' && !result && !error

  if (isCameraActive) {
    return (
      <CameraCapture
        onCapture={handleCapture}
        loading={loading}
        onClose={closeScan}
      />
    )
  }

  return (
    <div className="app">
      {activeTab !== 'home' && (
        <header className="app-header">
          <span className="brand-icon"><Icon name="logo" size={28} /></span>
          <h1 className="brand">NailIQ</h1>
          <p className="tagline">A precautionary nail-health screener</p>
        </header>
      )}

      <p className="disclaimer-banner">
        <Icon name="info" size={16} className="disclaimer-icon" /> This is an educational screening tool, not a
        diagnosis. It only flags whether your nail signs are typical or worth a doctor's look.
      </p>

      <div className="tab-fade" key={activeTab}>
        {activeTab === 'home' && <HomeScreen onStartScan={startScan} />}

        {activeTab === 'scan' && (
          <>
            {error && <div className="camera-error">{error}</div>}
            {result && (
              <ResultView result={result} onReset={handleReset} />
            )}
          </>
        )}

        {activeTab === 'learn' && <InfoSection />}
      </div>

      <BottomNav active={activeTab} onChange={setActiveTab} />
    </div>
  )
}

export default App
