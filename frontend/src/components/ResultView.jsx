import { useState } from 'react'
import { failureReasonMessage } from '../failureReasons'
import { submitFeedback } from '../api'
import Icon from './Icon'
import NailDiagram, { AnnotatedNailDiagram } from './NailDiagram'
import { conditionSummary, conditionNextStep } from '../conditions'
import { useI18n, findingName } from '../i18n'

const VERDICT_ICON = { within: 'checkCircle', outside: 'alertTriangle', inconclusive: 'helpCircle' }

function mlLabelText(t, label) {
  if (!label) return null
  const key = `result.mlLabels.${label}`
  const text = t(key)
  return text === key ? null : text
}

// Localize the backend's skin-tone caveat by its stable `tone_tier` key (same
// pattern as findingName()), falling back to the raw English string if the
// backend didn't send a tier -- backend and frontend can then ship on their
// own schedules without either one breaking.
function toneCaveatText(t, finding) {
  if (!finding.tone_caveat) return null
  if (finding.tone_tier) {
    const key = `result.toneCaveat.${finding.tone_tier}`
    const text = t(key)
    if (text !== key) return text
  }
  return finding.tone_caveat
}

// "Was this right?" -- the honest data path toward calibrating the heuristic
// thresholds. Fire-and-forget; a failed send shouldn't bother the user.
function FeedbackRow({ scanId, finding, showImpact }) {
  const { t } = useI18n()
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

  if (sent) {
    return (
      <p className="finding-feedback finding-feedback--thanks" role="status">
        {t('result.feedbackThanks')}
      </p>
    )
  }

  return (
    <div className="finding-feedback-wrap">
      <div className="finding-feedback">
        <span className="finding-feedback-q">{t('result.feedbackQ')}</span>
        <button type="button" className="feedback-btn" onClick={() => send(true)}>{t('result.feedbackYes')}</button>
        <button type="button" className="feedback-btn" onClick={() => send(false)}>{t('result.feedbackNo')}</button>
      </div>
      {showImpact && <p className="finding-feedback-impact">{t('result.feedbackImpact')}</p>}
    </div>
  )
}

function FindingCard({ finding, index, scanId, showFeedbackImpact }) {
  const { t } = useI18n()
  const verdictLabel = t(`verdict.${finding.verdict}.label`)
  const message =
    finding.verdict === 'inconclusive'
      ? failureReasonMessage(t, finding.failure_reason)
      : t(`verdict.${finding.verdict}.message`)

  const isMl = finding.track_used === 'ml'
  const isFused = finding.track_used === 'fused'
  const isColor = finding.track_used === 'color'
  const isColorFused = finding.track_used === 'color_fused'
  const matchLabel = isMl ? mlLabelText(t, finding.predicted_label) : null
  // Show the model's visual match only when its prediction actually drove this card
  // (agree / ml_primary); on color_only the top class is a different condition.
  const mlMatch = isFused
    ? mlLabelText(t, finding.ml?.predicted_label)
    : isColorFused && ['agree', 'ml_primary'].includes(finding.agreement)
      ? mlLabelText(t, finding.ml?.predicted_label)
      : null
  const agreementNote = isFused
    ? finding.agreement && t(`result.agreement.${finding.agreement}`) !== `result.agreement.${finding.agreement}`
      ? t(`result.agreement.${finding.agreement}`)
      : null
    : isColorFused
      ? finding.agreement && t(`result.colorAgreement.${finding.agreement}`) !== `result.colorAgreement.${finding.agreement}`
        ? t(`result.colorAgreement.${finding.agreement}`)
        : null
      : null

  // A visual reference for what the condition looks like, shown only when there's
  // something worth a closer look -- a "within" card doesn't need it, and showing
  // it there would just be clutter on the common case.
  const showDiagram = finding.verdict === 'outside' || finding.verdict === 'inconclusive'
  const summary = conditionSummary(t, finding.label)
  const toneCaveat = toneCaveatText(t, finding)

  return (
    <div className="finding-card" style={{ '--finding-delay': `${index * 50}ms` }}>
      {isMl && <span className="track-badge">{t('result.badgeMl')}</span>}
      {isFused && <span className="track-badge">{t('result.badgeFused')}</span>}
      {isColor && <span className="track-badge">{t('result.badgeColor')}</span>}
      {isColorFused && <span className="track-badge">{t('result.badgeColorFused')}</span>}
      <div className={`result-icon result-icon--${finding.verdict}`}>
        <Icon name={VERDICT_ICON[finding.verdict] ?? 'helpCircle'} size={22} />
      </div>
      <div className="finding-name">{findingName(t, finding)}</div>
      {finding.value != null && (
        <div className="result-angle">
          {finding.value.toFixed(1)}
          {finding.unit === 'deg' ? '°' : ''}
        </div>
      )}
      <div className={`result-verdict ${finding.verdict}`}>{verdictLabel}</div>
      {matchLabel && (
        <p className="result-match">
          {t('result.closestMatch', { label: matchLabel, pct: Math.round(finding.confidence * 100) })}
        </p>
      )}
      {agreementNote && <p className="result-match">{agreementNote}</p>}
      {mlMatch && finding.verdict !== 'inconclusive' && (
        <p className="result-match">{t('result.mlClosestMatch', { label: mlMatch })}</p>
      )}
      <p className="result-message">{message}</p>
      {toneCaveat && finding.verdict !== 'inconclusive' && (
        <p className="result-tone-caveat">
          <Icon name="info" size={14} />
          {toneCaveat}
        </p>
      )}
      {showDiagram && summary && (
        <div className="finding-diagram-section">
          <NailDiagram type={finding.label} />
          <p className="finding-summary">{summary}</p>
        </div>
      )}
      <FeedbackRow scanId={scanId} finding={finding} showImpact={showFeedbackImpact} />
    </div>
  )
}

// Two views of the same top-down photo: the box showing exactly which nail
// area the color checks measured, and (when the CNN track ran) a Grad-CAM
// heatmap showing where the AI model actually looked -- transparency beats a
// number or a prediction the user can't see the basis for. A toggle switches
// between them rather than showing both at once, since they're both full-width
// annotated photos and stacking them would push the result cards far down.
function MeasuredOverlay({ topImage, bbox, gradcam }) {
  const { t } = useI18n()
  const [view, setView] = useState('measured')
  if (!topImage || !bbox) return null
  const [x0, y0, x1, y1] = bbox
  const showGradcam = gradcam && view === 'gradcam'

  return (
    <div className="measured-overlay">
      <div className="measured-overlay-frame">
        {showGradcam ? (
          <img src={`data:image/jpeg;base64,${gradcam}`} alt={t('result.gradcamAlt')} />
        ) : (
          <>
            <img src={`data:image/jpeg;base64,${topImage}`} alt={t('result.photoAlt')} />
            <div
              className="measured-box"
              style={{
                left: `${x0 * 100}%`,
                top: `${y0 * 100}%`,
                width: `${(x1 - x0) * 100}%`,
                height: `${(y1 - y0) * 100}%`,
              }}
            />
          </>
        )}
      </div>
      {gradcam && (
        <div className="measured-overlay-toggle" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={view === 'measured'}
            className={view === 'measured' ? 'active' : ''}
            onClick={() => setView('measured')}
          >
            {t('result.measuredToggle')}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === 'gradcam'}
            className={view === 'gradcam' ? 'active' : ''}
            onClick={() => setView('gradcam')}
          >
            {t('result.gradcamToggle')}
          </button>
        </div>
      )}
      <p className="measured-caption">{showGradcam ? t('result.gradcamCaption') : t('result.measuredCaption')}</p>
    </div>
  )
}

// --- Top dashboard: scan confidence, attention level, image quality ----------

const QUALITY_ICON = { good: 'checkCircle', fair: 'helpCircle', poor: 'alertTriangle' }
const QUALITY_ISSUE_KEY = { blurry: 'result.issueBlurry', glare: 'result.issueGlare', polish: 'result.issuePolish' }
const BAND_ORDER = { good: 2, fair: 1, poor: 0 }

// Overall image quality = the worse of the two photos (a scan is only as good as
// its weakest shot), with that photo's issues named.
function combineQuality(t, imageQuality) {
  if (!imageQuality) return null
  const photos = [
    { which: t('result.sidePhoto'), q: imageQuality.side },
    { which: t('result.topPhoto'), q: imageQuality.top },
  ].filter((p) => p.q)
  if (photos.length === 0) return null
  const worst = photos.reduce((a, b) => (BAND_ORDER[b.q.band] < BAND_ORDER[a.q.band] ? b : a))
  const issues = (worst.q.issues ?? []).map((i) => (QUALITY_ISSUE_KEY[i] ? t(QUALITY_ISSUE_KEY[i]) : i))
  return { band: worst.q.band, which: worst.which, issues }
}

const QUALITY_LABEL_KEY = { good: 'result.qualityGood', fair: 'result.qualityFair', poor: 'result.qualityPoor' }

function ScanDashboard({ findings, imageQuality }) {
  const { t } = useI18n()
  const conclusive = findings.filter((f) => f.verdict !== 'inconclusive')
  const inconclusiveCount = findings.length - conclusive.length

  // Scan confidence: mean per-finding confidence over findings we could actually
  // analyze. Reuses the per-finding confidence; not a new model output.
  const meanConf =
    conclusive.length > 0
      ? conclusive.reduce((s, f) => s + (f.confidence ?? 0), 0) / conclusive.length
      : null

  // Attention level (NOT a risk score): noisy-OR over outside findings so several
  // signs accumulate but the total stays bounded at 100. We lead with a plain word
  // (Low/Some/High) so the number is interpretable at a glance.
  const outside = findings.filter((f) => f.verdict === 'outside')
  const attention = Math.round(
    100 * (1 - outside.reduce((prod, f) => prod * (1 - (f.confidence ?? 0)), 1)),
  )
  const attentionBand = attention >= 60 ? 'poor' : attention >= 30 ? 'fair' : 'good'
  const attentionWord = attention >= 60 ? t('result.high') : attention >= 30 ? t('result.some') : t('result.low')

  const quality = combineQuality(t, imageQuality)

  return (
    <div className="scan-dashboard">
      <div className="dashboard-tile">
        <span className="tile-label">{t('result.howSure')}</span>
        <span className="tile-value">{meanConf == null ? '--' : `${Math.round(meanConf * 100)}%`}</span>
        <span className="tile-sub">
          {conclusive.length === 0
            ? t('result.noSignsRead')
            : inconclusiveCount > 0
              ? inconclusiveCount === 1
                ? t('result.signsUnreadOne')
                : t('result.signsUnread', { n: inconclusiveCount })
              : t('result.inTheseReadings')}
        </span>
      </div>

      <div className="dashboard-tile">
        <span className="tile-label">{t('result.worthFollowingUp')}</span>
        <span className={`tile-value tile-value--${attentionBand}`}>
          {attentionWord}<span className="tile-value-max">{attention}/100</span>
        </span>
        <div className={`attention-meter attention-meter--${attentionBand}`}>
          <div className="attention-meter-fill" style={{ width: `${attention}%` }} />
        </div>
        <span className="meter-ends"><span>{t('result.low')}</span><span>{t('result.high')}</span></span>
        <span className="tile-sub">{t('result.notARiskScore')}</span>
      </div>

      <div className="dashboard-tile">
        <span className="tile-label">{t('result.photoQuality')}</span>
        {quality ? (
          <>
            <span className={`tile-value tile-value--${quality.band}`}>
              <Icon name={QUALITY_ICON[quality.band]} size={18} />
              {t(QUALITY_LABEL_KEY[quality.band])}
            </span>
            <span className="tile-sub">
              {quality.issues.length > 0
                ? `${quality.which}: ${quality.issues.join(', ')}`
                : t('result.bothClear')}
            </span>
          </>
        ) : (
          <span className="tile-value">--</span>
        )}
      </div>
    </div>
  )
}

// Aggregated guidance, driven by what the scan actually found. Reuses the
// per-condition "what to do" copy; invents no new medical wording.
function NextSteps({ outside, inconclusive }) {
  const { t } = useI18n()
  if (outside.length > 0) {
    return (
      <section className="next-steps next-steps--outside">
        <h3 className="next-steps-title">
          <Icon name="alertTriangle" size={18} /> {t('result.nextSteps')}
        </h3>
        <p className="next-steps-lead">{t('result.nextStepsOutside')}</p>
        <ul className="next-steps-list">
          {outside.map((f) => (
            <li key={f.label}>
              <strong>{findingName(t, f)}:</strong>{' '}
              {conditionNextStep(t, f.label) ?? t('result.nextStepsFallback')}
            </li>
          ))}
        </ul>
        <p className="next-steps-doctor">{t('result.nextStepsDoctor')}</p>
      </section>
    )
  }

  if (inconclusive.length > 0) {
    return (
      <section className="next-steps next-steps--inconclusive">
        <h3 className="next-steps-title">
          <Icon name="helpCircle" size={18} /> {t('result.nextSteps')}
        </h3>
        <p className="next-steps-lead">
          {inconclusive.length === 1
            ? t('result.nextStepsInconclusiveOne')
            : t('result.nextStepsInconclusive', { n: inconclusive.length })}
        </p>
      </section>
    )
  }

  return (
    <section className="next-steps next-steps--within">
      <h3 className="next-steps-title">
        <Icon name="checkCircle" size={18} /> {t('result.nextSteps')}
      </h3>
      <p className="next-steps-lead">{t('result.nextStepsWithin')}</p>
    </section>
  )
}

function ResultSummary({ outside, inconclusive, total }) {
  const { t } = useI18n()
  let verdict = 'within'
  let label = t('result.summaryWithin')
  if (outside.length > 0) {
    verdict = 'outside'
    label = outside.length === 1
      ? t('result.summaryOutsideOne')
      : t('result.summaryOutside', { n: outside.length })
  } else if (inconclusive.length > 0 && inconclusive.length === total) {
    verdict = 'inconclusive'
    label = t('result.summaryInconclusive')
  }
  return (
    <div className={`result-summary result-summary--${verdict}`} role="status">
      <div className={`result-icon result-icon--${verdict}`}>
        <Icon name={VERDICT_ICON[verdict]} size={22} />
      </div>
      <p className="result-summary-text">{label}</p>
    </div>
  )
}

export default function ResultView({ result, topImage, onReset }) {
  const { t, lang } = useI18n()
  const findings = result.findings ?? []
  const scanId = result.scan_id ?? null
  const bbox = result.overlay?.top_bbox_norm ?? null
  const gradcam = result.overlay?.gradcam ?? null
  const imageQuality = result.image_quality ?? null

  const outside = findings.filter((f) => f.verdict === 'outside')
  const inconclusive = findings.filter((f) => f.verdict === 'inconclusive')
  const within = findings.filter((f) => f.verdict === 'within')

  // Show the "your answers help calibrate future results" note once, on the
  // first feedback prompt the user actually sees -- repeating it under every
  // card would just be clutter.
  const firstFeedbackLabel = outside[0]?.label ?? within[0]?.label ?? null

  let idx = 0

  return (
    <div className="result-card">
      <div className="print-only-header">
        <h1>{t('result.reportTitle')}</h1>
        <p>{new Date().toLocaleDateString(lang, { year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>
      <ResultSummary outside={outside} inconclusive={inconclusive} total={findings.length} />
      <ScanDashboard findings={findings} imageQuality={imageQuality} />
      <AnnotatedNailDiagram findings={findings} />
      <NextSteps outside={outside} inconclusive={inconclusive} />
      <MeasuredOverlay topImage={topImage} bbox={bbox} gradcam={gradcam} />

      {outside.length > 0 && (
        <section className="result-group">
          <h3 className="result-group-title">{t('result.groupCloserLook')}</h3>
          <div className="findings-list">
            {outside.map((f) => (
              <FindingCard
                key={f.label}
                finding={f}
                index={idx++}
                scanId={scanId}
                showFeedbackImpact={f.label === firstFeedbackLabel}
              />
            ))}
          </div>
        </section>
      )}

      {inconclusive.length > 0 && (
        <section className="result-group">
          <h3 className="result-group-title">{t('result.groupCouldntAnalyze')}</h3>
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
            {t('result.withinCount', { n: within.length })}
            <span className="within-chevron"><Icon name="chevronRight" size={16} /></span>
          </summary>
          <div className="findings-list">
            {within.map((f) => (
              <FindingCard
                key={f.label}
                finding={f}
                index={idx++}
                scanId={scanId}
                showFeedbackImpact={f.label === firstFeedbackLabel}
              />
            ))}
          </div>
        </details>
      )}

      <div className="result-actions">
        <button type="button" className="secondary-btn" onClick={() => window.print()}>
          {t('result.savePrint')}
        </button>
        <button type="button" className="secondary-btn" onClick={onReset}>
          {t('result.scanAgain')}
        </button>
      </div>

      <p className="result-disclaimer">{t('result.disclaimer')}</p>
      <p className="result-sources">{t('result.sources')}</p>
    </div>
  )
}
