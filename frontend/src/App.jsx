import { useState, useCallback } from 'react'
import CameraCapture from './components/CameraCapture'
import ResultView from './components/ResultView'
import InfoSection from './components/InfoSection'
import HomeScreen from './components/HomeScreen'
import HistoryView from './components/HistoryView'
import BottomNav from './components/BottomNav'
import SettingsSheet from './components/SettingsSheet'
import Icon from './components/Icon'
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

  const handleCapture = useCallback(async ({ sideImage, topImage }) => {
    setLoading(true)
    setError(null)
    setTopImage(topImage)
    try {
      const data = await analyzeImages({ sideImage, topImage })
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
      <button
        type="button"
        className="settings-fab"
        aria-label={t('settings.open')}
        onClick={() => setSettingsOpen(true)}
      >
        <Icon name="settings" size={20} />
      </button>

      {activeTab !== 'home' && (
        <header className="app-header">
          <span className="brand-icon"><Icon name="logo" size={28} /></span>
          <h1 className="brand">NailIQ</h1>
          <p className="tagline">{t('app.tagline')}</p>
        </header>
      )}

      <p className="disclaimer-banner">
        <Icon name="info" size={16} className="disclaimer-icon" />
        <span>{t('app.disclaimer')}</span>
      </p>

      <div className="tab-fade" key={activeTab}>
        {activeTab === 'home' && (
          <HomeScreen onStartScan={startScan} onViewHistory={() => setActiveTab('history')} />
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
      </div>

      <BottomNav active={activeTab} onChange={setActiveTab} />

      {settingsOpen && <SettingsSheet onClose={() => setSettingsOpen(false)} />}
    </div>
  )
}

export default App
