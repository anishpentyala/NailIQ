import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'
import { getOnDeviceState, subscribeOnDevice } from '../ondevice'

export default function PrivacySheet({ onClose }) {
  const { t } = useI18n()
  const sheetRef = useRef(null)
  const [device, setDevice] = useState(getOnDeviceState)
  useEffect(() => subscribeOnDevice(setDevice), [])
  const onDevice = device.phase === 'ready'

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
        aria-label={t('privacy.title')}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-handle" aria-hidden="true" />

        <div className="sheet-header">
          <span className="sheet-header-icon">
            <Icon name="info" size={22} />
          </span>
          <div className="sheet-header-text">
            <h2 className="sheet-title">{t('privacy.title')}</h2>
          </div>
          <button type="button" className="sheet-close" onClick={onClose} aria-label={t('privacy.close')}>
            <Icon name="x" size={22} />
          </button>
        </div>

        <div className="sheet-body">
          <h3 className="settings-group-title">{t('privacy.photosTitle')}</h3>
          <p className="settings-row-desc">{t(onDevice ? 'privacy.photosBodyDevice' : 'privacy.photosBody')}</p>

          <h3 className="settings-group-title">{t('privacy.storedTitle')}</h3>
          <p className="settings-row-desc">{t(onDevice ? 'privacy.storedBodyDevice' : 'privacy.storedBody')}</p>

          <h3 className="settings-group-title">{t('privacy.notCollectedTitle')}</h3>
          <p className="settings-row-desc">{t('privacy.notCollectedBody')}</p>

          {!onDevice && (
            <>
              <h3 className="settings-group-title">{t('privacy.limitationTitle')}</h3>
              <p className="settings-row-desc">{t('privacy.limitationBody')}</p>
            </>
          )}

          <p className="settings-note">{t('privacy.disclaimer')}</p>
        </div>
      </div>
    </div>
  )
}
