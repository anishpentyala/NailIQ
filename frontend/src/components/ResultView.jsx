import { useState } from 'react'
import { failureReasonMessage } from '../failureReasons'
import { submitFeedback } from '../api'
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
  cyanosis: 'a bluish (cyanosis-type) appearance',
  terrys_nails: "a Terry's-nail-type appearance",
  beaus_lines: "a Beau's-line-type groove",
  muehrckes_lines: "a Muehrcke's-line-type banding",
  pitting: 'a pitting-type surface',
}

// How the two tracks lined up, shown on fused cards so the result is honest
// about where it came from.
const AGREEMENT_NOTE = {
  agree: 'The shape measurement and the AI model agree on this.',
  geometry_only: 'Based on the shape measurement; the AI model wasn’t conclusive here.',
}

// Same idea for the color/texture track: how the classical color check lined up
// with the color AI model (which leads when it has a confident call).
const COLOR_AGREEMENT_NOTE = {
  agree: 'The color check and the AI model agree on this.',
  color_only: 'Based on the color check; the AI model wasn’t conclusive here.',
  ml_primary: 'Based mainly on the AI model here.',
}

// "Was this right?" -- the honest data path toward calibrating the heuristic
// thresholds. Fire-and-forget; a failed send shouldn't bother the user.
function FeedbackRow({ scanId, finding }) {
  const [sent, setSent] = useState(false)
  if (finding.verdict === 'inconclusive') return null

  const send = (agreed) => {
    setSent(true)
    submitFeedback({
      scanId,
      label: finding.label,
      shownVerdict: finding.verdict,
      agreed,
    }).catch(() => {})
  }

  if (sent) return <p className="finding-feedback finding-feedback--thanks">Thanks — that helps us improve.</p>

  return (
    <div className="finding-feedback">
      <span className="finding-feedback-q">Does this match what you see?</span>
      <button type="button" className="feedback-btn" onClick={() => send(true)}>Yes</button>
      <button type="button" className="feedback-btn" onClick={() => send(false)}>No</button>
    </div>
  )
}

function FindingCard({ finding, index, scanId }) {
  const copy = COPY[finding.verdict] ?? COPY.inconclusive
  const message =
    finding.verdict === 'inconclusive' ? failureReasonMessage(finding.failure_reason) : copy.message

  const isMl = finding.track_used === 'ml'
  const isFused = finding.track_used === 'fused'
  const isColor = finding.track_used === 'color'
  const isColorFused = finding.track_used === 'color_fused'
  const matchLabel = isMl && finding.predicted_label ? ML_LABELS[finding.predicted_label] : null
  // Show the model's visual match only when its prediction actually drove this card
  // (agree / ml_primary); on color_only the top class is a different condition.
  const mlMatch = isFused
    ? (finding.ml?.predicted_label ? ML_LABELS[finding.ml.predicted_label] : null)
    : isColorFused && ['agree', 'ml_primary'].includes(finding.agreement)
      ? ML_LABELS[finding.ml?.predicted_label]
      : null
  const agreementNote = isFused
    ? AGREEMENT_NOTE[finding.agreement]
    : isColorFused
      ? COLOR_AGREEMENT_NOTE[finding.agreement]
      : null

  return (
    <div className="finding-card" style={{ '--finding-delay': `${index * 50}ms` }}>
      {isMl && <span className="track-badge">AI model</span>}
      {isFused && <span className="track-badge">Geometry + AI</span>}
      {isColor && <span className="track-badge">Color check</span>}
      {isColorFused && <span className="track-badge">Color + AI</span>}
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
      <FeedbackRow scanId={scanId} finding={finding} />
    </div>
  )
}

// The box on the user's own photo showing exactly which nail area the color
// checks measured -- transparency beats a number they can't see the basis for.
function MeasuredOverlay({ topImage, bbox }) {
  if (!topImage || !bbox) return null
  const [x0, y0, x1, y1] = bbox
  return (
    <div className="measured-overlay">
      <div className="measured-overlay-frame">
        <img src={`data:image/jpeg;base64,${topImage}`} alt="Your top-down nail photo" />
        <div
          className="measured-box"
          style={{
            left: `${x0 * 100}%`,
            top: `${y0 * 100}%`,
            width: `${(x1 - x0) * 100}%`,
            height: `${(y1 - y0) * 100}%`,
          }}
        />
      </div>
      <p className="measured-caption">The box shows the nail area the color checks measured.</p>
    </div>
  )
}

function ResultSummary({ outside, inconclusive }) {
  let verdict = 'within'
  let label = 'Everything looks within the typical range.'
  if (outside.length > 0) {
    verdict = 'outside'
    label = `${outside.length} ${outside.length === 1 ? 'sign is' : 'signs are'} outside the typical range.`
  } else if (inconclusive.length > 0 && inconclusive.length === outside.length + inconclusive.length) {
    verdict = 'inconclusive'
    label = "We couldn't analyze this scan — try retaking your photos."
  }
  return (
    <div className={`result-summary result-summary--${verdict}`}>
      <div className={`result-icon result-icon--${verdict}`}>
        <Icon name={COPY[verdict].icon} size={22} />
      </div>
      <p className="result-summary-text">{label}</p>
    </div>
  )
}

export default function ResultView({ result, topImage, onReset }) {
  const findings = result.findings ?? []
  const scanId = result.scan_id ?? null
  const bbox = result.overlay?.top_bbox_norm ?? null

  const outside = findings.filter((f) => f.verdict === 'outside')
  const inconclusive = findings.filter((f) => f.verdict === 'inconclusive')
  const within = findings.filter((f) => f.verdict === 'within')

  let idx = 0

  return (
    <div className="result-card">
      <ResultSummary outside={outside} inconclusive={inconclusive} />
      <MeasuredOverlay topImage={topImage} bbox={bbox} />

      {outside.length > 0 && (
        <section className="result-group">
          <h3 className="result-group-title">Worth a closer look</h3>
          <div className="findings-list">
            {outside.map((f) => (
              <FindingCard key={f.label} finding={f} index={idx++} scanId={scanId} />
            ))}
          </div>
        </section>
      )}

      {inconclusive.length > 0 && (
        <section className="result-group">
          <h3 className="result-group-title">Couldn’t analyze</h3>
          <div className="findings-list">
            {inconclusive.map((f) => (
              <FindingCard key={f.label} finding={f} index={idx++} scanId={scanId} />
            ))}
          </div>
        </section>
      )}

      {within.length > 0 && (
        <details className="within-group">
          <summary className="within-summary">
            <Icon name="checkCircle" size={18} />
            {within.length} within typical range
            <span className="within-chevron"><Icon name="chevronRight" size={16} /></span>
          </summary>
          <div className="findings-list">
            {within.map((f) => (
              <FindingCard key={f.label} finding={f} index={idx++} scanId={scanId} />
            ))}
          </div>
        </details>
      )}

      <div className="result-actions">
        <button type="button" className="secondary-btn" onClick={() => window.print()}>
          Save / print report
        </button>
        <button type="button" className="secondary-btn" onClick={onReset}>
          Scan again
        </button>
      </div>

      <p className="result-disclaimer">
        NailIQ is an educational screening tool, not a medical device. It does not
        diagnose any condition. Always consult a doctor about health concerns.
      </p>
      <p className="result-sources">
        Method &amp; honesty: the clubbing-angle threshold follows Hsu et&nbsp;al. (2024);
        the color and texture checks use uncalibrated heuristic thresholds and are
        screening signals, not measurements. Color readings adjust for lighting and
        skin tone, but real-world accuracy is unverified.
      </p>
    </div>
  )
}
