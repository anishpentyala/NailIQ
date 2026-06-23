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

function FindingCard({ finding, index }) {
  const copy = COPY[finding.verdict] ?? COPY.inconclusive
  const message =
    finding.verdict === 'inconclusive' ? failureReasonMessage(finding.failure_reason) : copy.message

  const isMl = finding.track_used === 'ml'
  const matchLabel = isMl && finding.predicted_label ? ML_LABELS[finding.predicted_label] : null

  return (
    <div className="finding-card" style={{ '--finding-delay': `${index * 70}ms` }}>
      {isMl && <span className="track-badge">AI model</span>}
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
