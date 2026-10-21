import { useEffect, useMemo, useRef, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'
import { CONDITION_ICONS, signNameParts } from '../conditions'
import { markOnboarded } from '../onboardingState'
import nailPhoto from '../assets/onboarding-nail.webp'

// Where on this healthy nail each sign is looked for, as fractions of the (fingertip-up) photo. Illustration anchors
// for the intro, not detections.
const IMG_W = 900
const IMG_H = 1820
const IMG_AR = IMG_W / IMG_H
const POINTS = {
  onychogryphosis: { x: 0.49, y: 0.252 },
  onycholysis: { x: 0.64, y: 0.285 },
  splinter_hemorrhages: { x: 0.36, y: 0.3 },
  leukonychia: { x: 0.6, y: 0.36 },
  pitting: { x: 0.38, y: 0.38 },
  cyanosis: { x: 0.48, y: 0.42 },
  koilonychia: { x: 0.275, y: 0.42 },
  beaus_lines: { x: 0.56, y: 0.47 },
}

const SHAPE_SIGNS = ['koilonychia', 'pitting', 'beaus_lines', 'onychogryphosis']

// scroll steps: welcome, one per sign (top of the nail to the bottom), then the closing screen
const STEPS = [
  { id: 'welcome' },
  ...['onychogryphosis', 'onycholysis', 'splinter_hemorrhages', 'leukonychia', 'pitting', 'cyanosis', 'koilonychia', 'beaus_lines']
    .map((sign) => ({ id: sign, sign })),
  { id: 'photos' },
]

const NAIL_CENTER = { x: 0.49, y: 0.385 }
const ease = (x) => x * x * (3 - 2 * x)
const lerp = (a, b, t) => a + (b - a) * t

// The example nail photo with the sign points drawn over it (SVG in the photo's own coordinates).
function NailPhoto({ activeSign, mode }) {
  return (
    <div className="ob-nail">
      <img className="ob-nail-img" src={nailPhoto} alt="" draggable="false" />
      <svg className="ob-nail-overlay" viewBox={`0 0 ${IMG_W} ${IMG_H}`} aria-hidden="true">
        <defs>
          <linearGradient id="obScan" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#3ddbb3" stopOpacity="0" />
            <stop offset="0.5" stopColor="#3ddbb3" stopOpacity="0.5" />
            <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
          </linearGradient>
          <radialGradient id="obZone">
            <stop offset="0" stopColor="#3ddbb3" stopOpacity="0.5" />
            <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
          </radialGradient>
          <clipPath id="obNailClip"><rect x="236" y="436" width="410" height="520" rx="150" /></clipPath>
        </defs>
        {mode === 'all' && <g clipPath="url(#obNailClip)"><rect className="ob-scan" x="236" y="436" width="410" height="160" fill="url(#obScan)" /></g>}
        {Object.entries(POINTS).map(([key, p]) => {
          const active = activeSign === key
          const dim = mode === 'none' || (mode === 'focus' && !active)
          return (
            <g key={key} className={`ob-point ${active ? 'is-active' : ''} ${dim ? 'is-dim' : ''}`} transform={`translate(${p.x * IMG_W} ${p.y * IMG_H})`}>
              <circle className="ob-point-zone" r="120" fill="url(#obZone)" />
              <circle className="ob-point-ring" r="40" />
              <circle className="ob-point-core" r="17" />
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// Camera pose for a step so that `focus` (SVG units) lands at the target spot of a W x H stage. The transform is
// applied about the camera box center, so d = target - center - s * R(r) * (focus - center).
function poseFor(step, index, W, H) {
  const Wc = H * IMG_AR
  const toLocal = (pt) => ({ x: pt.x * Wc - Wc / 2, y: pt.y * H - H / 2 })
  let focus = NAIL_CENTER
  let s = 0.85
  let r = 0
  let tx = 0.5
  let ty = 0.36
  if (step.sign) {
    focus = POINTS[step.sign]
    const side = index % 2 === 0 ? 1 : -1
    s = 1.35
    r = 9 * side
    tx = 0.5 + 0.14 * -side // finger swings left/right as you scroll
    ty = 0.32
  } else if (step.id === 'photos') {
    s = 0.7
    ty = 0.34
  }
  const p = toLocal(focus)
  const rad = (r * Math.PI) / 180
  const rx = Math.cos(rad) * p.x - Math.sin(rad) * p.y
  const ry = Math.sin(rad) * p.x + Math.cos(rad) * p.y
  return { s, r, dx: tx * W - W / 2 - s * rx, dy: ty * H - H / 2 - s * ry }
}

export default function Onboarding({ onDone }) {
  const { t } = useI18n()
  const scrollerRef = useRef(null)
  const [size, setSize] = useState({ W: 390, H: 844 })
  const [f, setF] = useState(0) // fractional step index driven by scroll
  const reduced = typeof document !== 'undefined' && document.documentElement.classList.contains('a11y-reduce-motion')
  const stepPx = Math.max(300, size.H * 0.5)
  const last = STEPS.length - 1

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    const measure = () => setSize({ W: el.clientWidth, H: el.clientHeight })
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    const onScroll = () => setF(Math.min(last, Math.max(0, el.scrollTop / stepPx)))
    onScroll()
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [stepPx, last])

  const poses = useMemo(() => STEPS.map((s, i) => poseFor(s, i, size.W, size.H)), [size.W, size.H])
  const i = reduced ? Math.round(f) : Math.min(Math.floor(f), last - 1)
  const k = reduced ? 0 : ease(f - i)
  const a = poses[i]
  const b = poses[reduced ? i : Math.min(i + 1, last)]
  const cam = { s: lerp(a.s, b.s, k), r: lerp(a.r, b.r, k), dx: lerp(a.dx, b.dx, k), dy: lerp(a.dy, b.dy, k) }
  const stepIdx = Math.min(last, Math.round(f))
  const step = STEPS[stepIdx]
  const mode = step.id === 'welcome' ? 'all' : step.id === 'photos' ? 'none' : 'focus'
  const Wc = size.H * IMG_AR

  const finish = () => {
    markOnboarded()
    onDone()
  }

  const name = step.sign ? signNameParts(t(`findingNames.${step.sign}`)) : null
  const group = step.sign ? (SHAPE_SIGNS.includes(step.sign) ? 'shape' : 'color') : null

  return (
    <div className="onboarding" role="dialog" aria-modal="true" aria-label={t('onboarding.label')}>
      <div className="ob-scroller" ref={scrollerRef} tabIndex={0}>
        <div className="ob-track" style={{ height: size.H + stepPx * last }}>
          <div className="ob-sticky" style={{ height: size.H }}>
            <div className="ob-stage">
              <div
                className="ob-camera"
                style={{
                  width: Wc,
                  height: size.H,
                  left: (size.W - Wc) / 2,
                  transform: `translate(${cam.dx}px, ${cam.dy}px) rotate(${cam.r}deg) scale(${cam.s})`,
                }}
              >
                <NailPhoto activeSign={step.sign ?? null} mode={mode} />
              </div>
              <span className="ob-example">{t('onboarding.example')}</span>
            </div>

            <div className="ob-top">
              <div className="ob-progress" aria-hidden="true"><span style={{ width: `${(f / last) * 100}%` }} /></div>
              {stepIdx < last && (
                <button type="button" className="ob-skip" onClick={finish}>{t('onboarding.skip')}</button>
              )}
            </div>

            <div className="ob-panel" aria-live="polite">
              <div className="ob-card" key={step.id}>
                {step.sign ? (
                  <>
                    <span className="ob-kicker">
                      <Icon name={CONDITION_ICONS[step.sign]} size={14} /> {t(`onboarding.${group}Title`)}
                    </span>
                    <h2 className="ob-title">{name.term}</h2>
                    <p className="ob-text">{t(`conditions.${step.sign}.summary`)}</p>
                  </>
                ) : (
                  <>
                    <h2 className="ob-title">{t(`onboarding.${step.id}Title`)}</h2>
                    <p className="ob-text">{t(`onboarding.${step.id}Text`)}</p>
                  </>
                )}
                {step.id === 'welcome' && (
                  <p className="ob-hint"><Icon name="chevronRight" size={14} className="rot-down" /> {t('onboarding.scrollHint')}</p>
                )}
                {step.id === 'photos' && (
                  <>
                    <p className="ob-fine">{t('app.disclaimer')}</p>
                    <button type="button" className="primary-btn ob-start" onClick={finish}>{t('onboarding.start')}</button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
