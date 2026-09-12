import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'

// iOS-style nav bar: a large title that scrolls away, leaving a glass bar with
// a compact title behind it. The collapse is driven by an IntersectionObserver
// on a sentinel pinned to the bottom of the large title rather than a scroll
// listener, so it fires twice per transition instead of once per frame.
export default function NavBar({ title, scrollRef, onOpenSettings }) {
  const { t } = useI18n()
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
    <>
      <div className={`navbar ${collapsed ? 'is-collapsed' : ''}`}>
        <span className="navbar-title-compact">{title}</span>
        <button
          type="button"
          className="navbar-action"
          aria-label={t('settings.open')}
          onClick={onOpenSettings}
        >
          <Icon name="settings" size={20} />
        </button>
      </div>

      <h1 className="navbar-large">
        {title}
        <span ref={sentinelRef} className="navbar-sentinel" aria-hidden="true" />
      </h1>
    </>
  )
}
