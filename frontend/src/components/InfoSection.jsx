import { useState, useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import Icon from './Icon'
import NailDiagram from './NailDiagram'

import { getConditions } from '../conditions'
import { useI18n } from '../i18n'

function ConditionSheet({ condition, onClose }) {
  const { t } = useI18n()
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  // Portal to #root so the overlay's containing block is the app viewport, not
  // the transformed `.tab-fade` tab wrapper (its `animation: ... both` pins a
  // `transform`, which would otherwise trap this absolute overlay to the padded
  // tab box and leave the app's edges uncovered).
  return createPortal(
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
          <button type="button" className="sheet-close" onClick={onClose} aria-label={t('info.close')}>
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
    </div>,
    document.getElementById('root'),
  )
}

export default function InfoSection() {
  const { t } = useI18n()
  const conditions = useMemo(() => getConditions(t), [t])
  const [openKey, setOpenKey] = useState(null)
  const openCondition = openKey ? conditions.find((c) => c.key === openKey) : null

  return (
    <div className="info-section">
      <p className="info-intro">{t('info.intro')}</p>

      <div className="info-group">
        {conditions.map((condition) => (
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

      <section className="info-equity">
        <span className="info-equity-icon"><Icon name="checkCircle" /></span>
        <div>
          <p className="info-point-title">{t('info.equityTitle')}</p>
          <p className="info-point-text">{t('info.equityText')}</p>
        </div>
      </section>

      {openCondition && (
        <ConditionSheet condition={openCondition} onClose={() => setOpenKey(null)} />
      )}
    </div>
  )
}
