import { useEffect, useRef } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'

// Every disclaimer and limitation in the app lives here (Settings -> Disclaimers & limitations); the screens
// themselves stay clean. Text is reused from the existing translated strings.
const ITEMS = [
  'app.disclaimer',
  'result.disclaimer',
  'privacy.disclaimer',
  'result.notARiskScore',
  'home.whoFor',
  'home.notYet',
  'result.limitedNote',
  'result.toneCaveat.limited',
  'result.toneCaveat.minimal',
  'crop.appearanceNote',
  'history.trendNote',
  'result.sources',
]

export default function DisclaimerSheet({ onClose }) {
  const { t } = useI18n()
  const sheetRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    sheetRef.current?.focus({ preventScroll: true })
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div
        ref={sheetRef}
        className="sheet settings-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={t('settings.disclaimersTitle')}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-handle" aria-hidden="true" />
        <div className="sheet-header">
          <span className="sheet-header-icon">
            <Icon name="info" size={22} />
          </span>
          <div className="sheet-header-text">
            <h2 className="sheet-title">{t('settings.disclaimersTitle')}</h2>
          </div>
          <button type="button" className="sheet-close" onClick={onClose} aria-label={t('settings.disclaimersClose')}>
            <Icon name="x" size={22} />
          </button>
        </div>
        <div className="sheet-body">
          {ITEMS.map((key) => (
            <p key={key} className="settings-row-desc disclaimer-item">{t(key)}</p>
          ))}
        </div>
      </div>
    </div>
  )
}
