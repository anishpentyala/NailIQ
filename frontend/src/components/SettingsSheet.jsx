import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import PrivacySheet from './PrivacySheet'
import { useI18n, LANGUAGES } from '../i18n'

function Toggle({ id, label, description, checked, onChange }) {
  return (
    <div className="settings-row">
      <div className="settings-row-text">
        <label className="settings-row-label" htmlFor={id}>{label}</label>
        <p className="settings-row-desc" id={`${id}-desc`}>{description}</p>
      </div>
      <button
        type="button"
        id={id}
        role="switch"
        aria-checked={checked}
        aria-describedby={`${id}-desc`}
        className={`settings-switch ${checked ? 'settings-switch--on' : ''}`}
        onClick={() => onChange(!checked)}
      >
        <span className="settings-switch-thumb" aria-hidden="true" />
      </button>
    </div>
  )
}

export default function SettingsSheet({ onClose }) {
  const { t, lang, setLang, highContrast, largeText, reduceMotion, darkMode, setPref } = useI18n()
  const sheetRef = useRef(null)
  const [privacyOpen, setPrivacyOpen] = useState(false)

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    sheetRef.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div
        ref={sheetRef}
        className="sheet settings-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={t('settings.title')}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-handle" aria-hidden="true" />

        <header className="sheet-header">
          <span className="sheet-header-icon">
            <Icon name="settings" size={22} />
          </span>
          <div className="sheet-header-text">
            <h2 className="sheet-title">{t('settings.title')}</h2>
            <p className="sheet-subtitle">{t('app.settingsLabel')}</p>
          </div>
          <button type="button" className="sheet-close" onClick={onClose} aria-label={t('settings.close')}>
            <Icon name="x" size={22} />
          </button>
        </header>

        <div className="sheet-body">
          <h3 className="settings-group-title" id="settings-language-label">{t('settings.language')}</h3>
          <div className="settings-lang-group" role="radiogroup" aria-labelledby="settings-language-label">
            {LANGUAGES.map(({ code, name }) => (
              <button
                key={code}
                type="button"
                role="radio"
                aria-checked={lang === code}
                lang={code}
                className={`settings-lang-btn ${lang === code ? 'settings-lang-btn--active' : ''}`}
                onClick={() => setLang(code)}
              >
                {name}
                {lang === code && <Icon name="checkCircle" size={16} />}
              </button>
            ))}
          </div>

          <h3 className="settings-group-title">{t('settings.display')}</h3>
          <Toggle
            id="setting-dark-mode"
            label={t('settings.darkMode')}
            description={t('settings.darkModeDesc')}
            checked={darkMode}
            onChange={(on) => setPref('darkMode', on)}
          />
          <Toggle
            id="setting-contrast"
            label={t('settings.highContrast')}
            description={t('settings.highContrastDesc')}
            checked={highContrast}
            onChange={(on) => setPref('highContrast', on)}
          />
          <Toggle
            id="setting-large-text"
            label={t('settings.largeText')}
            description={t('settings.largeTextDesc')}
            checked={largeText}
            onChange={(on) => setPref('largeText', on)}
          />
          <Toggle
            id="setting-reduce-motion"
            label={t('settings.reduceMotion')}
            description={t('settings.reduceMotionDesc')}
            checked={reduceMotion}
            onChange={(on) => setPref('reduceMotion', on)}
          />

          <button
            type="button"
            className="settings-link"
            onClick={() => setPrivacyOpen(true)}
          >
            <Icon name="info" size={16} />
            {t('settings.privacyLink')}
          </button>

          <p className="settings-note">{t('settings.note')}</p>
        </div>
      </div>

      {privacyOpen && <PrivacySheet onClose={() => setPrivacyOpen(false)} />}
    </div>
  )
}
