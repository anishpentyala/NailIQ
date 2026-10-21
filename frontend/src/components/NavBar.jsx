import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'
import lockupDark from '../assets/logo-lockup.svg'
import lockupLight from '../assets/logo-lockup-light.svg'

// iOS-style nav bar: a large title that scrolls away, leaving a glass bar with
// a compact title behind it. The collapse is driven by an IntersectionObserver
// on a sentinel pinned to the bottom of the large title rather than a scroll
// listener, so it fires twice per transition instead of once per frame.
export default function NavBar({ title, brand, scrollRef, onOpenSettings }) {
  const { t, darkMode } = useI18n()
  const lockup = darkMode ? lockupDark : lockupLight
  const sentinelRef = useRef(null)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      ([entry]) => setCollapsed(!entry.isIntersecting),
      { root: scrollRef.current, threshold: 0 },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [scrollRef])

  return (
    <header className="navbar-wrap">
      <div className={`navbar ${collapsed ? 'is-collapsed' : ''}`}>
        <span className="navbar-title-compact">{brand ? <img className="navbar-logo-compact" src={lockup} alt={title} /> : title}</span>
        <button
          type="button"
          className="navbar-action"
          aria-label={t('settings.open')}
          onClick={onOpenSettings}
        >
          <Icon name="settings" size={20} />
        </button>
      </div>

      <h1 className={`navbar-large ${brand ? 'navbar-large--brand' : ''}`}>
        {brand ? <img className="navbar-logo" src={lockup} alt={title} /> : title}
        <span ref={sentinelRef} className="navbar-sentinel" aria-hidden="true" />
      </h1>
    </header>
  )
}
