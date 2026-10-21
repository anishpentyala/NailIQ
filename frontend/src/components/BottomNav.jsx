import Icon from './Icon'
import { useI18n } from '../i18n'

const LEFT = [
  { key: 'home', icon: 'home' },
  { key: 'history', icon: 'history' },
]
const RIGHT = [
  { key: 'learn', icon: 'book' },
  { key: 'settings', icon: 'settings' },
]

export default function BottomNav({ active, onChange, onOpenSettings }) {
  const { t } = useI18n()
  const item = (tab) => (
    <button
      key={tab.key}
      type="button"
      className={`bottom-nav-item ${active === tab.key ? 'active' : ''}`}
      aria-current={active === tab.key ? 'page' : undefined}
      onClick={() => (tab.key === 'settings' ? onOpenSettings() : onChange(tab.key))}
    >
      <Icon name={tab.icon} className="bottom-nav-icon" />
      <span className="bottom-nav-label">{tab.key === 'settings' ? t('settings.title') : t(`nav.${tab.key}`)}</span>
    </button>
  )
  return (
    <nav className="bottom-nav" aria-label={t('nav.label')}>
      {LEFT.map(item)}
      <button
        type="button"
        className={`bottom-nav-scan ${active === 'scan' ? 'active' : ''}`}
        aria-label={t('nav.scan')}
        aria-current={active === 'scan' ? 'page' : undefined}
        onClick={() => onChange('scan')}
      >
        <Icon name="camera" size={26} />
      </button>
      {RIGHT.map(item)}
    </nav>
  )
}
