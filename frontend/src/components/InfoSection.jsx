import { useState, useEffect } from 'react'
import Icon from './Icon'
import NailDiagram from './NailDiagram'

import { CONDITIONS } from '../conditions'

function ConditionSheet({ condition, onClose }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={condition.name}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-handle" aria-hidden="true" />

        <header className="sheet-header">
          <span className="sheet-header-icon">
            <Icon name={condition.icon} size={22} />
          </span>
          <div className="sheet-header-text">
            <h2 className="sheet-title">{condition.name}</h2>
            <p className="sheet-subtitle">{condition.summary}</p>
          </div>
          <button type="button" className="sheet-close" onClick={onClose} aria-label="Close">
            <Icon name="x" size={22} />
          </button>
        </header>

        <div className="sheet-body">
          {condition.lead && <p className="sheet-lead">{condition.lead}</p>}

          <div className="diagram-wrap">
            <NailDiagram type={condition.key} />
          </div>

          {condition.points.map((point) => (
            <div key={point.title} className="info-point">
              <span className="info-point-icon">
                <Icon name={point.icon} />
              </span>
              <div>
                <p className="info-point-title">{point.title}</p>
                <p className="info-point-text">{point.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const BY_KEY = Object.fromEntries(CONDITIONS.map((c) => [c.key, c]))

export default function InfoSection() {
  const [openKey, setOpenKey] = useState(null)
  const openCondition = openKey ? BY_KEY[openKey] : null

  return (
    <div className="info-section">
      <p className="info-intro">
        NailIQ screens every photo for all of these signs. Tap any one to learn what it looks
        like, why it happens, and what your result means.
      </p>

      <div className="info-group">
        {CONDITIONS.map((condition) => (
          <button
            key={condition.key}
            type="button"
            className="info-card"
            onClick={() => setOpenKey(condition.key)}
          >
            <span className="info-icon">
              <Icon name={condition.icon} />
            </span>
            <span className="info-name">{condition.name}</span>
            <span className="info-chevron">
              <Icon name="chevronRight" size={18} />
            </span>
          </button>
        ))}
      </div>

      {openCondition && (
        <ConditionSheet condition={openCondition} onClose={() => setOpenKey(null)} />
      )}
    </div>
  )
}
