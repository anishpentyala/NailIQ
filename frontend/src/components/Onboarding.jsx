import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'
import { CONDITION_ICONS, signNameParts } from '../conditions'
import { markOnboarded } from '../onboardingState'
import nailPhoto from '../assets/onboarding-nail.webp'

// A handful of example signs (deliberately not the full list). Anchors are fractions of the fingertip-up photo;
// they are illustration spots for the intro, not detections.
const IMG_W = 900
const IMG_H = 1820
const IMG_AR = IMG_W / IMG_H
const NAIL_X = 0.49

// One scroll section each: the text scrolls like a normal page while the sticky photo flies to that section's pose.
// `side` is where the text sits; a sign's own point (focus) is pinned to the free side of the screen at (tx, ty), so
// the card never covers it. Everything else is free choreography: zoom s, spin r, 3D lean rx/ry (degrees).
const SECTIONS = [
  { id: 'welcome', wide: true, focus: { x: NAIL_X, y: 0.385 }, tx: 0.5, ty: 0.36, s: 0.8, r: 0, rx: 16, ry: -8 },
  { id: 'koilonychia', side: 'left', group: 'shape', dot: { x: 0.58, y: 0.27 }, tx: 0.72, ty: 0.38, s: 1.3, r: -14, rx: 8, ry: -30 },
  { id: 'leukonychia', side: 'right', group: 'color', dot: { x: 0.42, y: 0.34 }, tx: 0.28, ty: 0.62, s: 2.0, r: 24, rx: -14, ry: 14 },
  { id: 'pitting', side: 'left', group: 'shape', dot: { x: 0.55, y: 0.4 }, tx: 0.72, ty: 0.3, s: 1.5, r: 85, rx: 0, ry: 0 },
  { id: 'cyanosis', side: 'right', group: 'color', dot: { x: 0.42, y: 0.47 }, tx: 0.28, ty: 0.45, s: 1.35, r: -28, rx: 14, ry: -16 },
  { id: 'photos', wide: true, focus: { x: NAIL_X, y: 0.385 }, tx: 0.5, ty: 0.3, s: 0.68, r: 0, rx: 0, ry: 0 },
].map((sec) => ({ ...sec, focus: sec.focus ?? sec.dot }))
const SIGN_SECTIONS = SECTIONS.filter((s) => s.dot)

const PERSPECTIVE = 1100
const ease = (x) => x * x * (3 - 2 * x)
const lerp = (a, b, t) => a + (b - a) * t
const clamp01 = (x) => Math.min(1, Math.max(0, x))

// The example nail photo with the sign points drawn over it (SVG in the photo's own coordinates).
function NailPhoto({ near }) {
  return (
    <div className="ob-nail">
      <img className="ob-nail-img" src={nailPhoto} alt="" draggable="false" />
      <svg className="ob-nail-overlay" viewBox={`0 0 ${IMG_W} ${IMG_H}`} aria-hidden="true">
        <defs>
          <radialGradient id="obZone">
            <stop offset="0" stopColor="#3ddbb3" stopOpacity="0.5" />
            <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
          </radialGradient>
        </defs>
        {SIGN_SECTIONS.map((p) => (
          <g
            key={p.id}
            className={`ob-point ${near[p.id] > 0.6 ? 'is-active' : ''}`}
            style={{ '--near': near[p.id] }}
            transform={`translate(${p.dot.x * IMG_W} ${p.dot.y * IMG_H})`}
          >
            <circle className="ob-point-zone" r="120" fill="url(#obZone)" />
            <circle className="ob-point-ring" r="40" />
            <circle className="ob-point-core" r="17" />
          </g>
        ))}
      </svg>
    </div>
  )
}

export default function Onboarding({ onDone }) {
  const { t } = useI18n()
  const scrollerRef = useRef(null)
  const [size, setSize] = useState({ W: 390, H: 844 })
  const [y, setY] = useState(0)
  const reduced = typeof document !== 'undefined' && document.documentElement.classList.contains('a11y-reduce-motion')

  // section heights (px) and the scroll position at which each section's text is centered
  const heights = SECTIONS.map((sec) => (sec.id === 'welcome' ? size.H : size.H * 0.95))
  const tops = heights.map((_, i) => heights.slice(0, i).reduce((a, b) => a + b, 0))
  const maxScroll = heights.reduce((a, b) => a + b, 0) - size.H
  const anchors = SECTIONS.map((_, i) => Math.min(maxScroll, Math.max(0, tops[i] + heights[i] / 2 - size.H / 2)))

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
    const onScroll = () => setY(el.scrollTop)
    onScroll()
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  // which two sections we are between, and how far (0..1) toward the next
  let i = 0
  while (i < SECTIONS.length - 2 && y >= anchors[i + 1]) i += 1
  const span = Math.max(1, anchors[i + 1] - anchors[i])
  let u = clamp01((y - anchors[i]) / span)
  u = reduced ? Math.round(u) : ease(u)
  const A = SECTIONS[i]
  const B = SECTIONS[i + 1]
  const pose = {
    fx: lerp(A.focus.x, B.focus.x, u),
    fy: lerp(A.focus.y, B.focus.y, u),
    tx: lerp(A.tx, B.tx, u),
    ty: lerp(A.ty, B.ty, u),
    s: lerp(A.s, B.s, u),
    r: lerp(A.r, B.r, u),
    rx: lerp(A.rx, B.rx, u),
    ry: lerp(A.ry, B.ry, u),
  }

  // each sign's point glows while the camera is on (or arriving at) its section; the welcome view shows them all softly
  const near = {}
  SIGN_SECTIONS.forEach((p) => {
    const w = (A.id === p.id ? 1 - u : 0) + (B.id === p.id ? u : 0)
    const soft = A.id === 'welcome' ? (1 - u) * 0.5 : 0
    near[p.id] = clamp01(Math.max(w, soft))
  })

  // Place photo point (fx, fy) at screen (tx, ty). The camera box is transformed about its center as
  // perspective(d) translate(dx, dy) rotateX rotateY rotate scale, so push the point through the same rotations and
  // perspective divide, then solve for the translation.
  const Wc = size.H * IMG_AR
  const rad = (v) => (v * Math.PI) / 180
  const lx = (pose.fx * Wc - Wc / 2) * pose.s
  const ly = (pose.fy * size.H - size.H / 2) * pose.s
  const x1 = Math.cos(rad(pose.r)) * lx - Math.sin(rad(pose.r)) * ly
  const y1 = Math.sin(rad(pose.r)) * lx + Math.cos(rad(pose.r)) * ly
  const x2 = Math.cos(rad(pose.ry)) * x1
  const z2 = -Math.sin(rad(pose.ry)) * x1
  const y3 = Math.cos(rad(pose.rx)) * y1 - Math.sin(rad(pose.rx)) * z2
  const z3 = Math.sin(rad(pose.rx)) * y1 + Math.cos(rad(pose.rx)) * z2
  const k = PERSPECTIVE / (PERSPECTIVE - z3)
  const dx = (pose.tx * size.W - size.W / 2) / k - x2
  const dy = (pose.ty * size.H - size.H / 2) / k - y3

  const finish = () => {
    markOnboarded()
    onDone()
  }
  const lastSection = y >= maxScroll - 4

  return (
    <div className="onboarding" role="dialog" aria-modal="true" aria-label={t('onboarding.label')}>
      <div className="ob-top">
        <div className="ob-progress" aria-hidden="true"><span style={{ width: `${maxScroll ? (y / maxScroll) * 100 : 0}%` }} /></div>
        {!lastSection && <button type="button" className="ob-skip" onClick={finish}>{t('onboarding.skip')}</button>}
      </div>

      <div className="ob-scroller" ref={scrollerRef} tabIndex={0}>
        <div className="ob-track">
          <div className="ob-sticky" style={{ height: size.H }}>
            <div
              className="ob-camera"
              style={{
                width: Wc,
                height: size.H,
                left: (size.W - Wc) / 2,
                transform: `perspective(${PERSPECTIVE}px) translate(${dx}px, ${dy}px) rotateX(${pose.rx}deg) rotateY(${pose.ry}deg) rotate(${pose.r}deg) scale(${pose.s})`,
              }}
            >
              <NailPhoto near={near} />
            </div>
            <span className="ob-example">{t('onboarding.example')}</span>
          </div>

          <div className="ob-secs" style={{ marginTop: -size.H }}>
            {SECTIONS.map((sec, k) => (
              <section
                key={sec.id}
                className={`ob-sec ${sec.wide ? 'ob-sec--wide' : `ob-sec--${sec.side}`}`}
                style={{ height: heights[k] }}
              >
                <div className="ob-card">
                  {sec.dot ? (
                    <>
                      <span className="ob-kicker">
                        <Icon name={CONDITION_ICONS[sec.id]} size={14} /> {t(`onboarding.${sec.group}Title`)}
                      </span>
                      <h2 className="ob-title">{signNameParts(t(`findingNames.${sec.id}`)).term}</h2>
                      <p className="ob-text">{t(`conditions.${sec.id}.summary`)}</p>
                      <p className="ob-lead">{t(`conditions.${sec.id}.lead`)}</p>
                    </>
                  ) : (
                    <>
                      <h2 className="ob-title">{t(`onboarding.${sec.id}Title`)}</h2>
                      <p className="ob-text">{t(`onboarding.${sec.id}Text`)}</p>
                    </>
                  )}
                  {sec.id === 'welcome' && (
                    <p className="ob-hint"><Icon name="chevronRight" size={14} className="rot-down" /> {t('onboarding.scrollHint')}</p>
                  )}
                  {sec.id === 'photos' && (
                    <>
                      <p className="ob-fine">{t('app.disclaimer')}</p>
                      <button type="button" className="primary-btn ob-start" onClick={finish}>{t('onboarding.start')}</button>
                    </>
                  )}
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
