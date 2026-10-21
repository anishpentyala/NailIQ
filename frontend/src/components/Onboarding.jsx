import { useEffect, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'
import { CONDITION_ICONS, signNameParts } from '../conditions'
import { markOnboarded } from '../onboardingState'

// Where on a healthy nail each sign is looked for. These are illustration anchors for the intro, not detections.
const POINTS = {
  onychogryphosis: { x: 120, y: 50 },
  onycholysis: { x: 152, y: 66 },
  splinter_hemorrhages: { x: 94, y: 78 },
  leukonychia: { x: 142, y: 104 },
  pitting: { x: 102, y: 118 },
  cyanosis: { x: 120, y: 152 },
  koilonychia: { x: 78, y: 150 },
  beaus_lines: { x: 134, y: 178 },
}

const SLIDES = [
  { id: 'welcome', signs: Object.keys(POINTS) },
  { id: 'shape', signs: ['koilonychia', 'pitting', 'beaus_lines', 'onychogryphosis'] },
  { id: 'color', signs: ['leukonychia', 'cyanosis', 'splinter_hemorrhages', 'onycholysis'] },
  { id: 'photos', signs: [] },
]

const CYCLE_MS = 2600

// A drawn (not photographed) healthy nail: skin, nail plate, lunula, cuticle fold, gloss. Illustration only.
function NailArt({ activeSign, dimSigns }) {
  const nail = 'M76 74C76 54 96 44 120 44S164 54 164 74V188C164 222 146 238 120 238S76 222 76 188Z'
  return (
    <svg className="ob-nail" viewBox="0 0 240 420" role="img" aria-hidden="true">
      <defs>
        <linearGradient id="obSkin" x1="0" x2="1">
          <stop offset="0" stopColor="#a9694a" />
          <stop offset="0.28" stopColor="#cf9170" />
          <stop offset="0.5" stopColor="#dca584" />
          <stop offset="0.72" stopColor="#cf9170" />
          <stop offset="1" stopColor="#a9694a" />
        </linearGradient>
        <linearGradient id="obPad" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#000" stopOpacity="0.25" />
          <stop offset="0.25" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#3a1a10" stopOpacity="0.35" />
        </linearGradient>
        <linearGradient id="obNail" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#f6d5ca" />
          <stop offset="0.3" stopColor="#efbcae" />
          <stop offset="1" stopColor="#e3978c" />
        </linearGradient>
        <linearGradient id="obGloss" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0.08" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <radialGradient id="obLunula" cx="0.5" cy="1" r="0.8">
          <stop offset="0" stopColor="#fbe9e2" stopOpacity="0.95" />
          <stop offset="1" stopColor="#fbe9e2" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="obScan" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#3ddbb3" stopOpacity="0" />
          <stop offset="0.5" stopColor="#3ddbb3" stopOpacity="0.55" />
          <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
        </linearGradient>
        <filter id="obBlur"><feGaussianBlur stdDeviation="3" /></filter>
        <clipPath id="obNailClip"><path d={nail} /></clipPath>
      </defs>

      {/* finger */}
      <path d="M52 420V122C52 54 82 20 120 20S188 54 188 122V420Z" fill="url(#obSkin)" />
      <path d="M52 420V122C52 54 82 20 120 20S188 54 188 122V420Z" fill="url(#obPad)" />
      <ellipse cx="120" cy="30" rx="44" ry="10" fill="#fff" opacity="0.12" filter="url(#obBlur)" />
      {/* knuckle creases */}
      <g fill="none" stroke="#6b3420" strokeOpacity="0.28" strokeLinecap="round" strokeWidth="2">
        <path d="M74 318C100 326 140 326 166 318" />
        <path d="M80 330C104 336 136 336 160 330" strokeOpacity="0.18" />
        <path d="M70 378C98 388 142 388 170 378" />
      </g>

      {/* nail fold shadow, plate, ridges, lunula, free edge, gloss */}
      <path d={nail} fill="#5a2a1c" opacity="0.4" filter="url(#obBlur)" transform="translate(0 2) scale(1.02) translate(-2.4 -2)" />
      <path d={nail} fill="url(#obNail)" />
      <g clipPath="url(#obNailClip)">
        <g stroke="#fff" strokeOpacity="0.09" strokeWidth="2">
          <path d="M96 50V230" /><path d="M110 46V234" /><path d="M124 46V234" /><path d="M138 48V232" /><path d="M152 52V228" />
        </g>
        <ellipse cx="120" cy="238" rx="38" ry="26" fill="url(#obLunula)" />
        <rect x="70" y="44" width="100" height="16" fill="#fff" opacity="0.4" />
        <path d="M76 74C76 54 96 44 120 44S164 54 164 74" fill="none" stroke="#fff" strokeOpacity="0.55" strokeWidth="3" />
        <path d="M82 60L112 40 138 40 96 150Z" fill="url(#obGloss)" />
        <rect className="ob-scan" x="70" y="40" width="100" height="46" fill="url(#obScan)" />
      </g>
      <path d={nail} fill="none" stroke="#7a3a2a" strokeOpacity="0.45" strokeWidth="2" />
      {/* cuticle fold over the base of the nail */}
      <path d="M74 214C86 246 154 246 166 214C162 236 150 252 120 252S78 236 74 214Z" fill="#cf9170" />
      <path d="M74 214C86 246 154 246 166 214" fill="none" stroke="#7a3a2a" strokeOpacity="0.4" strokeWidth="1.5" />

      {/* points: every sign's spot, dim; the active one glows */}
      {Object.entries(POINTS).map(([key, p]) => (
        <g key={key} className={`ob-point ${activeSign === key ? 'is-active' : ''} ${dimSigns.includes(key) ? 'is-dim' : ''}`} transform={`translate(${p.x} ${p.y})`}>
          <circle className="ob-point-ring" r="9" />
          <circle className="ob-point-core" r="4.2" />
        </g>
      ))}
    </svg>
  )
}

export default function Onboarding({ onDone }) {
  const { t } = useI18n()
  const [slide, setSlide] = useState(0)
  const [cursor, setCursor] = useState(0)
  const current = SLIDES[slide]
  const last = slide === SLIDES.length - 1
  const activeSign = current.signs.length > 0 && slide > 0 ? current.signs[cursor % current.signs.length] : null

  // step through the slide's signs one at a time
  useEffect(() => {
    if (slide === 0 || current.signs.length === 0) return
    const id = setInterval(() => setCursor((c) => (c + 1) % current.signs.length), CYCLE_MS)
    return () => clearInterval(id)
  }, [slide, current.signs.length])

  const go = (n) => {
    setSlide(n)
    setCursor(0)
  }
  const finish = () => {
    markOnboarded()
    onDone()
  }

  const name = activeSign ? signNameParts(t(`findingNames.${activeSign}`)) : null

  return (
    <div className="onboarding" role="dialog" aria-modal="true" aria-label={t('onboarding.label')}>
      <div className="ob-top">
        <div className="ob-dots" aria-hidden="true">
          {SLIDES.map((s, i) => <span key={s.id} className={`ob-dot ${i === slide ? 'is-on' : i < slide ? 'is-done' : ''}`} />)}
        </div>
        {!last && (
          <button type="button" className="ob-skip" onClick={finish}>{t('onboarding.skip')}</button>
        )}
      </div>

      <div className="ob-stage" data-slide={current.id}>
        <div className="ob-camera">
          <NailArt activeSign={activeSign} dimSigns={slide === 0 ? [] : slide === 3 ? Object.keys(POINTS) : SLIDES.flatMap((s) => (s.id === current.id ? [] : s.signs))} />
        </div>
        <span className="ob-example">{t('onboarding.example')}</span>
      </div>

      <div className="ob-panel">
        <h2 className="ob-title" key={`t${slide}`}>{t(`onboarding.${current.id}Title`)}</h2>
        <p className="ob-text" key={`p${slide}`}>{t(`onboarding.${current.id}Text`)}</p>

        {activeSign && (
          <div className="ob-sign" key={activeSign} aria-live="polite">
            <span className="ob-sign-icon"><Icon name={CONDITION_ICONS[activeSign]} size={18} /></span>
            <div className="ob-sign-text">
              <strong>{name.term}</strong>
              <span>{t(`conditions.${activeSign}.summary`)}</span>
            </div>
          </div>
        )}
        {slide > 0 && current.signs.length > 0 && (
          <div className="ob-sign-dots" aria-hidden="true">
            {current.signs.map((s, i) => <span key={s} className={i === cursor % current.signs.length ? 'is-on' : ''} />)}
          </div>
        )}
        {last && <p className="ob-fine">{t('app.disclaimer')}</p>}

        <div className="ob-actions">
          {slide > 0 && (
            <button type="button" className="ob-back" onClick={() => go(slide - 1)}>{t('onboarding.back')}</button>
          )}
          <button type="button" className="primary-btn ob-next" onClick={() => (last ? finish() : go(slide + 1))}>
            {last ? t('onboarding.start') : t('onboarding.next')}
          </button>
        </div>
      </div>
    </div>
  )
}
