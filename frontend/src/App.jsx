import { useState, useCallback, useRef } from 'react'
import CameraCapture from './components/CameraCapture'
import ResultView from './components/ResultView'
import InfoSection from './components/InfoSection'
import HomeScreen from './components/HomeScreen'
import HistoryView from './components/HistoryView'
import BottomNav from './components/BottomNav'
import SettingsSheet from './components/SettingsSheet'
import NavBar from './components/NavBar'
import Onboarding from './components/Onboarding'
import { hasOnboarded } from './onboardingState'
import { analyzeImages } from './api'
import { useI18n } from './i18n'
import './App.css'

function App() {
  const { t } = useI18n()
  const [activeTab, setActiveTab] = useState('home')
  const [result, setResult] = useState(null)
  const [topImage, setTopImage] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [intro, setIntro] = useState(() => !hasOnboarded() || new URLSearchParams(window.location.search).has('intro'))
  const scrollRef = useRef(null)

  const handleCapture = useCallback(async ({ sideImage, topImage, topNailBbox }) => {
    setLoading(true)
    setError(null)
    setTopImage(topImage)
    try {
      const data = await analyzeImages({ sideImage, topImage, topNailBbox })
      setResult(data)
    } catch {
      setError(t('app.serverError'))
    } finally {
      setLoading(false)
    }
  }, [t])

  const handleReset = useCallback(() => {
    setResult(null)
    setTopImage(null)
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

  // Finishing (or skipping) the intro always lands on Home, and drops ?intro from the address so a reload or a saved
  // bookmark does not replay it.
  const finishIntro = () => {
    setActiveTab('home')
    setResult(null)
    setError(null)
    setSettingsOpen(false)
    const url = new URL(window.location.href)
    if (url.searchParams.has('intro')) {
      url.searchParams.delete('intro')
      window.history.replaceState(null, '', url.pathname + url.search + url.hash)
    }
    setIntro(false)
  }

  if (intro) return <Onboarding onDone={finishIntro} />

  // go full-screen while the camera is active
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

  // Home is titled with the brand (never translated); the rest reuse their tab names.
  const title = activeTab === 'home' ? 'NailIQ' : t(`nav.${activeTab}`)

  return (
    <div className="app" ref={scrollRef}>
      <NavBar
        title={title}
        brand={activeTab === 'home'}
        scrollRef={scrollRef}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <main className="tab-fade" key={activeTab}>
        {activeTab === 'home' && (
          <HomeScreen onStartScan={startScan} />
        )}

        {activeTab === 'scan' && (
          <>
            {error && <div className="camera-error" role="alert">{error}</div>}
            {result && (
              <ResultView result={result} topImage={topImage} onReset={handleReset} />
            )}
          </>
        )}

        {activeTab === 'history' && <HistoryView />}

        {activeTab === 'learn' && <InfoSection />}
      </main>

      <BottomNav active={activeTab} onChange={setActiveTab} onOpenSettings={() => setSettingsOpen(true)} />

      {settingsOpen && (
        <SettingsSheet
          onClose={() => setSettingsOpen(false)}
          onReplayIntro={() => { setSettingsOpen(false); setIntro(true) }}
        />
      )}
    </div>
  )
}

export default App
