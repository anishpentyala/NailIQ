import { failureReasonMessage } from '../failureReasons'
import Icon from './Icon'

const COPY = {
  within: {
    icon: 'checkCircle',
    label: 'Within typical range',
    message:
      'Keep an eye on changes over time, and always follow up on any health concerns with a doctor.',
  },
  outside: {
    icon: 'alertTriangle',
    label: 'Outside typical range',
    message: 'This is worth showing a doctor. It is not a diagnosis.',
  },
  inconclusive: {
    icon: 'helpCircle',
    label: "Couldn't analyze this photo",
  },
}

const ML_LABELS = {
  clubbing: 'clubbing-type appearance',
  koilonychia: 'koilonychia-type (spoon) appearance',
  healthy: 'a typical, healthy-looking nail',
}

// How the two tracks lined up, shown on fused cards so the result is honest
// about where it came from.
const AGREEMENT_NOTE = {
  agree: 'The shape measurement and the AI model agree on this.',
  geometry_only: 'Based on the shape measurement; the AI model wasn’t conclusive here.',
}

function FindingCard({ finding, index }) {
  const copy = COPY[finding.verdict] ?? COPY.inconclusive
  const message =
    finding.verdict === 'inconclusive' ? failureReasonMessage(finding.failure_reason) : copy.message

  const isMl = finding.track_used === 'ml'
  const isFused = finding.track_used === 'fused'
  const isColor = finding.track_used === 'color'
  const matchLabel = isMl && finding.predicted_label ? ML_LABELS[finding.predicted_label] : null
  const mlMatch = isFused && finding.ml?.predicted_label ? ML_LABELS[finding.ml.predicted_label] : null
  const agreementNote = isFused ? AGREEMENT_NOTE[finding.agreement] : null

  return (
    <div className="finding-card" style={{ '--finding-delay': `${index * 70}ms` }}>
      {isMl && <span className="track-badge">AI model</span>}
      {isFused && <span className="track-badge">Geometry + AI</span>}
      {isColor && <span className="track-badge">Color check</span>}
      <div className={`result-icon result-icon--${finding.verdict}`}>
        <Icon name={copy.icon} size={22} />
      </div>
      <div className="finding-name">{finding.display_name}</div>
      {finding.value != null && (
        <div className="result-angle">
          {finding.value.toFixed(1)}
          {finding.unit === 'deg' ? '°' : ''}
        </div>
      )}
      <div className={`result-verdict ${finding.verdict}`}>{copy.label}</div>
      {matchLabel && (
        <p className="result-match">
          Closest visual match: {matchLabel} · {Math.round(finding.confidence * 100)}% confidence
        </p>
      )}
      {agreementNote && <p className="result-match">{agreementNote}</p>}
      {mlMatch && finding.verdict !== 'inconclusive' && (
        <p className="result-match">AI model’s closest visual match: {mlMatch}</p>
      )}
      <p className="result-message">{message}</p>
    </div>
  )
}

export default function ResultView({ result, onReset }) {
  const findings = result.findings ?? []

  return (
    <div className="result-card">
      <div className="findings-list">
        {findings.map((finding, index) => (
          <FindingCard key={finding.label} finding={finding} index={index} />
        ))}
      </div>

      <button type="button" className="secondary-btn" onClick={onReset}>
        Scan again
      </button>

      <p className="result-disclaimer">
        NailIQ is an educational screening tool, not a medical device. It does not
        diagnose any condition. Always consult a doctor about health concerns.
      </p>
    </div>
  )
}
