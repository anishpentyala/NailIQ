const CONDITIONS = [
  {
    key: 'clubbing',
    icon: '🖐️',
    name: 'Digital clubbing',
    summary: 'A change in the angle where the nail meets the skin.',
    detail:
      "Clubbing is when the fingertip rounds out and the nail starts to curve over it, " +
      "losing the small dip normally seen between nail and skin. It's been linked to lung, " +
      "heart, and digestive conditions, though it can take months or years to develop and " +
      "isn't always tied to a disease. NailIQ measures the nail-to-skin angle from your " +
      "side-profile photo and flags whether it falls within the range typically seen.",
  },
  {
    key: 'koilonychia',
    icon: '🥄',
    name: 'Koilonychia (spoon nails)',
    summary: 'Nails that curve upward like a spoon instead of lying flat.',
    detail:
      'Koilonychia describes nails thin and concave enough to hold a drop of water. It is ' +
      'sometimes associated with iron-deficiency anemia or thyroid changes, but soft, slightly ' +
      "concave nails are also common and harmless on their own, especially in kids. NailIQ " +
      'measures how much your nail curves away from a straight line between cuticle and tip.',
  },
]

export default function InfoSection() {
  return (
    <div className="info-section">
      {CONDITIONS.map((condition) => (
        <details key={condition.key} className="info-card">
          <summary className="info-summary">
            <span className="info-icon">{condition.icon}</span>
            <span className="info-summary-text">
              <span className="info-name">{condition.name}</span>
              <span className="info-blurb">{condition.summary}</span>
            </span>
          </summary>
          <p className="info-detail">{condition.detail}</p>
        </details>
      ))}
    </div>
  )
}
