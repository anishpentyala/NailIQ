import Icon from './Icon'

const TABS = [
  { key: 'home', icon: 'home', label: 'Home' },
  { key: 'scan', icon: 'camera', label: 'Scan' },
  { key: 'learn', icon: 'book', label: 'Learn' },
]

export default function BottomNav({ active, onChange }) {
  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`bottom-nav-item ${active === tab.key ? 'active' : ''}`}
          onClick={() => onChange(tab.key)}
        >
          <Icon name={tab.icon} className="bottom-nav-icon" />
          <span className="bottom-nav-label">{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}
