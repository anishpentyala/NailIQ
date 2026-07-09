import Icon from './Icon'
import { useI18n } from '../i18n'

const TABS = [
  { key: 'home', icon: 'home' },
  { key: 'scan', icon: 'camera' },
  { key: 'history', icon: 'history' },
  { key: 'learn', icon: 'book' },
]

export default function BottomNav({ active, onChange }) {
  const { t } = useI18n()
  return (
    <nav className="bottom-nav" aria-label={t('nav.label')}>
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`bottom-nav-item ${active === tab.key ? 'active' : ''}`}
          aria-current={active === tab.key ? 'page' : undefined}
          onClick={() => onChange(tab.key)}
        >
          <Icon name={tab.icon} className="bottom-nav-icon" />
          <span className="bottom-nav-label">{t(`nav.${tab.key}`)}</span>
        </button>
      ))}
    </nav>
  )
}
