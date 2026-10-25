import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { SettingsProvider } from './i18n'
import { startOnDevice } from './ondevice'

// begin loading the on-device AI right away (a no-op when the bundle is not installed)
startOnDevice()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SettingsProvider>
      <App />
    </SettingsProvider>
  </StrictMode>,
)
