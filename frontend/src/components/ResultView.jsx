import { useEffect, useRef, useState } from 'react'
import { failureReasonMessage } from '../failureReasons'
import { submitFeedback } from '../api'
import Icon from './Icon'
import NailDiagram, { AnnotatedNailDiagram } from './NailDiagram'
import { conditionSummary, conditionNextStep, signNameParts, CONDITION_ICONS as CONDITION_ICON } from '../conditions'
import { useI18n, findingName } from '../i18n'

const VERDICT_ICON = { within: 'checkCircle', outside: 'alertTriangle', inconclusive: 'helpCircle' }

function mlLabelText(t, label) {
  if (!label) return null
  const key = `result.mlLabels.${label}`
  const text = t(key)
  return text === key ? null : text
}

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
  // CNN-only conditions (e.g. onychogryphosis) travel on the color track but have no color check
  const isAiOnly =
    finding.evidence_type === 'appearance' ||
    ['ml_only', 'ml_no_opinion'].includes(finding.agreement) ||
    finding.failure_reason === 'requires_ai_model'
  const isColor = finding.track_used === 'color' && !isAiOnly
  const isColorFused = finding.track_used === 'color_fused' && !isAiOnly
  const matchLabel = isMl ? mlLabelText(t, finding.predicted_label) : null

  // only show the model's visual match if its prediction actually drove this card
  let mlMatch = null
  if (isFused) {
    mlMatch = mlLabelText(t, finding.ml?.predicted_label)
  } else if (isColorFused && ['agree', 'ml_primary'].includes(finding.agreement)) {
    mlMatch = mlLabelText(t, finding.ml?.predicted_label)
  }

  let agreementNote = null
  if (isFused && finding.agreement) {
    const key = `result.agreement.${finding.agreement}`
    agreementNote = t(key) !== key ? t(key) : null
  } else if ((isColorFused || isAiOnly) && finding.agreement) {
    const key = `result.colorAgreement.${finding.agreement}`
    agreementNote = t(key) !== key ? t(key) : null
  }

  // only show the reference diagram when there's something worth a closer look
  const showDiagram = finding.verdict === 'outside' || finding.verdict === 'inconclusive'
  const summary = conditionSummary(t, finding.label)

  return (
    <div className="finding-card" id={`finding-${finding.label}`} style={{ '--finding-delay': `${index * 50}ms` }}>
      {(isMl || isAiOnly) && <span className="track-badge">{t(finding.evidence_type === 'appearance' ? 'crop.appearance' : 'result.badgeMl')}</span>}
      {isFused && <span className="track-badge">{t('result.badgeFused')}</span>}
      {isColor && <span className="track-badge">{t('result.badgeColor')}</span>}
      {isColorFused && <span className="track-badge">{t('result.badgeColorFused')}</span>}
      {finding.validation_tier === 'limited' && <span className="track-badge">{t('result.badgeLimited')}</span>}
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

// Scroll progress (0 -> 1) of the hero inside the app's scroll container. The photo "flies" over the finger as the
// user scrolls past the sign cards. With reduced motion it stays at 0 and every point is shown.
function useHeroProgress(ref) {
  const [p, setP] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el || document.documentElement.classList.contains('a11y-reduce-motion')) return
    const hero = el.closest('.scan-hero')
    const scroller = el.closest('.app')
    if (!hero || !scroller) return
    let raf = 0
    const update = () => {
      raf = 0
      const sr = scroller.getBoundingClientRect()
      const hr = hero.getBoundingClientRect()
      const travel = Math.max(1, hr.height - sr.height * 0.55)
      setP(Math.min(1, Math.max(0, (sr.top - hr.top) / travel)))
    }
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(update) }
    update()
    scroller.addEventListener('scroll', onScroll, { passive: true })
    return () => { scroller.removeEventListener('scroll', onScroll); if (raf) cancelAnimationFrame(raf) }
  }, [ref])
  return p
}

const ease = (x) => x * x * (3 - 2 * x)

// Circular close-up of the nail. The photo drifts and zooms as the page scrolls, visiting each point where the AI
// model's attention peaked (real Grad-CAM peaks from the backend); each point lights up when the view reaches it.
// The outline marks the area the color checks measured. Points show where the model looked, never what a sign is.
function HeroPhoto({ topImage, bbox, gradcam, attention, tone }) {
  const { t } = useI18n()
  const wrapRef = useRef(null)
  const progress = useHeroProgress(wrapRef)
  const reduced = typeof document !== 'undefined' && document.documentElement.classList.contains('a11y-reduce-motion')
  const [view, setView] = useState('measured')
  const [ar, setAr] = useState(1)
  if (!topImage) return null
  const showGradcam = gradcam && view === 'gradcam'

  const pts = (attention ?? []).slice(0, 3)
  let imgStyle = { left: 0, top: 0, width: '100%' }
  let box = null
  let dots = []
  if (bbox) {
    const [x0, y0, x1, y1] = bbox
    const bw = Math.max(x1 - x0, 0.04)
    const center = { x: (x0 + x1) / 2, y: (y0 + y1) / 2 }
    // waypoints: the measured nail first, then each attention point
    const way = [center, ...pts]
    const seg = way.length - 1
    const f = seg === 0 ? 0 : progress * seg
    const i = Math.min(Math.floor(f), Math.max(seg - 1, 0))
    const k = seg === 0 ? 0 : ease(f - i)
    const a = way[i]
    const b = way[Math.min(i + 1, way.length - 1)]
    const fx = a.x + (b.x - a.x) * k
    const fy = a.y + (b.y - a.y) * k
    const zoom = 1 + 0.25 * ease(Math.min(1, progress * 1.6)) // pushes in as the scan "locks on"
    const w = Math.max(55 / bw, 100, 100 * ar) * zoom // image width as % of the circle
    const h = w / ar
    const left = Math.min(0, Math.max(100 - w, 50 - fx * w)) // the focus point sits at the centre of the circle
    const top = Math.min(0, Math.max(100 - h, 50 - fy * h))
    imgStyle = { left: `${left}%`, top: `${top}%`, width: `${w}%` }
    box = { left: `${left + x0 * w}%`, top: `${top + y0 * h}%`, width: `${(x1 - x0) * w}%`, height: `${(y1 - y0) * h}%` }
    dots = pts.map((pt, n) => ({
      key: n,
      left: `${left + pt.x * w}%`,
      top: `${top + pt.y * h}%`,
      on: reduced || progress >= (n + 0.35) / (pts.length + 0.35) * 0.95,
      size: 0.7 + 0.5 * (pt.strength ?? 1),
    }))
  }

  return (
    <div className="hero-photo-wrap" ref={wrapRef}>
      <div className="hero-photo-sticky">
      <div className={`hero-photo hero-photo--${tone}`}>
        {showGradcam ? (
          <img className="hero-photo-img hero-photo-img--fill" src={`data:image/jpeg;base64,${gradcam}`} alt={t('result.gradcamAlt')} />
        ) : (
          <>
            <img
              className="hero-photo-img"
              style={imgStyle}
              src={`data:image/jpeg;base64,${topImage}`}
              alt={t('result.photoAlt')}
              onLoad={(e) => setAr(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight || 1)}
            />
            {box && <div className="hero-measure" style={box} />}
            {dots.map((d) => (
              <span key={d.key} className={`hero-point ${d.on ? 'is-on' : ''}`} style={{ left: d.left, top: d.top, '--s': d.size }} />
            ))}
          </>
        )}
        <div className="hero-scanline" aria-hidden="true" />
      </div>
      {gradcam && (
        <div className="hero-toggle" role="tablist">
          <button type="button" role="tab" aria-selected={view === 'measured'} className={view === 'measured' ? 'active' : ''} onClick={() => setView('measured')}>
            {t('result.measuredToggle')}
          </button>
          <button type="button" role="tab" aria-selected={view === 'gradcam'} className={view === 'gradcam' ? 'active' : ''} onClick={() => setView('gradcam')}>
            {t('result.gradcamToggle')}
          </button>
        </div>
      )}
      <p className="hero-photo-caption">
        {showGradcam ? t('result.gradcamCaption') : pts.length > 0 ? t('result.pointsCaption') : t('result.measuredCaption')}
      </p>
      </div>
    </div>
  )
}

function jumpToFinding(label) {
  const el = document.getElementById(`finding-${label}`)
  if (!el) return
  const details = el.closest('details')
  if (details) details.open = true
  const calm = document.documentElement.classList.contains('a11y-reduce-motion')
  el.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'center' })
  el.classList.remove('is-flash')
  void el.offsetWidth
  el.classList.add('is-flash')
}

function ScanHero({ findings, outside, inconclusive, topImage, bbox, gradcam, attention, onReset }) {
  const { t } = useI18n()
  let tone = 'within'
  let summary = t('result.summaryWithin')
  if (outside.length > 0) {
    tone = 'outside'
    summary = outside.length === 1 ? t('result.summaryOutsideOne') : t('result.summaryOutside', { n: outside.length })
  } else if (inconclusive.length > 0 && inconclusive.length === findings.length) {
    tone = 'inconclusive'
    summary = t('result.summaryInconclusive')
  }
  // worth-a-look first, then readable-and-fine, then couldn't-analyze
  const rank = { outside: 0, within: 1, inconclusive: 2 }
  const ordered = [...findings].sort((a, b) => rank[a.verdict] - rank[b.verdict])

  return (
    <section className={`scan-hero scan-hero--${tone}`} role="status">
      <div className="scan-hero-top">
        <button type="button" className="scan-hero-back" aria-label={t('result.scanAgain')} onClick={onReset}>
          <Icon name="chevronRight" size={20} className="flip-x" />
        </button>
        <h2 className="scan-hero-title">{t('result.scanResults')}</h2>
      </div>

      <div className="scan-hero-body">
        <div className="scan-hero-cards">
          {ordered.map((f, i) => (
            <button
              type="button"
              key={f.label}
              className={`sign-card sign-card--${f.verdict}`}
              style={{ '--finding-delay': `${i * 45}ms` }}
              onClick={() => jumpToFinding(f.label)}
            >
              <span className="sign-card-icon"><Icon name={CONDITION_ICON[f.label] ?? VERDICT_ICON[f.verdict]} size={16} /></span>
              <span className="sign-card-label">{signNameParts(findingName(t, f)).label}</span>
              <span className="sign-card-name">{signNameParts(findingName(t, f)).term}</span>
              <span className="sign-card-status">{t(`verdict.${f.verdict}.label`)}</span>
              {f.validation_tier === 'limited' && <span className="sign-card-tag">{t('result.badgeLimited')}</span>}
            </button>
          ))}
        </div>
        <HeroPhoto topImage={topImage} bbox={bbox} gradcam={gradcam} attention={attention} tone={tone} />
      </div>

      <div className="scan-hero-summary">
        <p className="scan-hero-summary-main">{summary}</p>
        <p className="scan-hero-summary-sub">{t('result.tapCard')}</p>
      </div>
    </section>
  )
}

const QUALITY_ICON = { good: 'checkCircle', fair: 'helpCircle', poor: 'alertTriangle' }
const QUALITY_ISSUE_KEY = { blurry: 'result.issueBlurry', glare: 'result.issueGlare', polish: 'result.issuePolish' }
const BAND_ORDER = { good: 2, fair: 1, poor: 0 }

// overall quality is just the worse of the two photos
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

  // average confidence across the findings we could actually read
  const meanConf =
    conclusive.length > 0
      ? conclusive.reduce((s, f) => s + (f.confidence ?? 0), 0) / conclusive.length
      : null

  // attention level (not a risk score) - combines all the "outside" findings into one 0-100 number
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

  // only show the feedback-impact note once, on the first card the user sees
  const firstFeedbackLabel = outside[0]?.label ?? within[0]?.label ?? null

  let idx = 0

  return (
    <div className="result-card">
      <div className="print-only-header">
        <h1>{t('result.reportTitle')}</h1>
        <p>{new Date().toLocaleDateString(lang, { year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>
      <ScanHero
        findings={findings}
        outside={outside}
        inconclusive={inconclusive}
        topImage={topImage}
        bbox={bbox}
        gradcam={gradcam}
        attention={result.overlay?.attention_points ?? []}
        onReset={onReset}
      />
      <div className="print-only-block">
        <ResultSummary outside={outside} inconclusive={inconclusive} total={findings.length} />
      </div>
      <ScanDashboard findings={findings} imageQuality={imageQuality} />
      <AnnotatedNailDiagram findings={findings} />
      <NextSteps outside={outside} inconclusive={inconclusive} />

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

      <p className="result-one-line">{t('result.oneLine')}</p>
      <div className="print-only-block">
        <p className="result-disclaimer">{t('result.disclaimer')}</p>
        <p className="result-sources">{t('result.sources')}</p>
      </div>
    </div>
  )
}
