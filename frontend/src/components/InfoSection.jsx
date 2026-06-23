import { useState, useEffect } from 'react'
import Icon from './Icon'
import NailDiagram from './NailDiagram'

const CONDITIONS = [
  {
    key: 'clubbing',
    icon: 'finger',
    name: 'Digital clubbing',
    summary: 'A change in the angle where the nail meets the skin.',
    lead:
      'Look at your finger from the side. Most fingers have a small notch where the nail ' +
      'meets the skin. Clubbing slowly smooths that notch away until the fingertip looks ' +
      'rounded and the nail curves over it.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          "Normally there's a small dip where your nail meets the skin of your finger, like a " +
          'tiny valley. With clubbing, that dip flattens out or disappears, the fingertip looks ' +
          'rounder and puffier, and over time the nail can start to curve down over the tip ' +
          'instead of lying flat.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          "Doctors aren't fully sure why it happens, but it shows up most often alongside " +
          'long-term lung problems, certain heart conditions, or some digestive diseases. It ' +
          "builds up slowly over months or years, so it's not something that appears overnight.",
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We measure the angle where your nail meets your skin from the side-profile photo. ' +
          "A typical angle stays under about 180°. Clubbing pushes that angle past it, so it's " +
          'really just careful geometry, not a guess.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'An "outside typical range" result does not mean you have a specific disease — it ' +
          'just means it is worth showing a doctor, especially if you have also noticed things ' +
          'like shortness of breath, a lingering cough, or unusual tiredness.',
      },
    ],
  },
  {
    key: 'koilonychia',
    icon: 'spoon',
    name: 'Koilonychia (spoon nails)',
    summary: 'Nails that curve upward like a spoon instead of lying flat.',
    lead:
      'Look straight down at your nail. A typical nail is flat or gently domed. A spoon nail ' +
      'dips inward in the middle — sometimes deep enough that a drop of water would sit in it ' +
      'instead of rolling off.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'Instead of staying flat or curving gently outward, the middle of the nail dips ' +
          'inward, like a tiny spoon. In more noticeable cases, the nail is thin and curved ' +
          'enough that a drop of water would actually sit in the dip instead of rolling off.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'The most common cause is low iron in the blood, also called iron-deficiency anemia. ' +
          'It can also show up with thyroid changes, some skin conditions, or a lot of exposure ' +
          'to solvents and harsh detergents. In babies and young kids, slightly spoon-shaped ' +
          'nails are often totally normal and grow out on their own.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We measure how far the middle of your nail curves away from a straight line drawn ' +
          'between your cuticle and fingertip, then scale that by the length of your nail so it ' +
          'works fairly across different finger sizes.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'An "outside typical range" result is worth mentioning to a doctor, especially if you ' +
          'also feel unusually tired, look pale, or have brittle nails — those can point toward ' +
          'anemia, which is easy to test for with a simple blood test and easy to treat.',
      },
    ],
  },
]

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

export default function InfoSection() {
  const [openKey, setOpenKey] = useState(null)
  const openCondition = CONDITIONS.find((c) => c.key === openKey) ?? null

  return (
    <div className="info-section">
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
          <span className="info-summary-text">
            <span className="info-name">{condition.name}</span>
            <span className="info-blurb">{condition.summary}</span>
          </span>
          <span className="info-chevron">
            <Icon name="chevronRight" size={18} />
          </span>
        </button>
      ))}

      {openCondition && (
        <ConditionSheet condition={openCondition} onClose={() => setOpenKey(null)} />
      )}
    </div>
  )
}
