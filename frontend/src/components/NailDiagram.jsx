import clubbingComparisonImg from '../assets/diagrams/clubbing-comparison.png'
import koilonychiaComparisonImg from '../assets/diagrams/koilonychia-comparison.png'
import leukonychiaComparisonImg from '../assets/diagrams/leukonychia-comparison.png'
import melanonychiaComparisonImg from '../assets/diagrams/melanonychia-comparison.png'
import pallorComparisonImg from '../assets/diagrams/pallor-comparison.png'
import cyanosisComparisonImg from '../assets/diagrams/cyanosis-comparison.png'
import terrysNailsComparisonImg from '../assets/diagrams/terrys_nails-comparison.png'
import lindsaysNailsComparisonImg from '../assets/diagrams/lindsays_nails-comparison.png'
import onycholysisComparisonImg from '../assets/diagrams/onycholysis-comparison.png'
import beausLinesComparisonImg from '../assets/diagrams/beaus_lines-comparison.png'
import muehrckesLinesComparisonImg from '../assets/diagrams/muehrckes_lines-comparison.png'
import splinterHemorrhagesComparisonImg from '../assets/diagrams/splinter_hemorrhages-comparison.png'
import pittingComparisonImg from '../assets/diagrams/pitting-comparison.png'
import { useI18n, findingName } from '../i18n'

// Conditions with a real comparison illustration; their alt text lives in the
// locale dictionaries under diagram.imgAlts so it translates with the UI.
const COMPARISON_IMAGES = {
  clubbing: clubbingComparisonImg,
  koilonychia: koilonychiaComparisonImg,
  leukonychia: leukonychiaComparisonImg,
  melanonychia: melanonychiaComparisonImg,
  pallor: pallorComparisonImg,
  cyanosis: cyanosisComparisonImg,
  terrys_nails: terrysNailsComparisonImg,
  lindsays_nails: lindsaysNailsComparisonImg,
  onycholysis: onycholysisComparisonImg,
  beaus_lines: beausLinesComparisonImg,
  muehrckes_lines: muehrckesLinesComparisonImg,
  splinter_hemorrhages: splinterHemorrhagesComparisonImg,
  pitting: pittingComparisonImg,
}

/* ---- Top-down nail plate, for the color / surface conditions ---- */
const PLATE_BASE = {
  pallor: 'plate-pale',
  cyanosis: 'plate-blue',
  terrys_nails: 'plate-white',
  lindsays_nails: 'plate-white',
}

function plateOverlay(pattern) {
  switch (pattern) {
    case 'leukonychia':
      return (
        <>
          <ellipse className="mark-white" cx="208" cy="68" rx="7" ry="5" />
          <ellipse className="mark-white" cx="231" cy="90" rx="6" ry="4" />
          <ellipse className="mark-white" cx="214" cy="110" rx="5" ry="4" />
        </>
      )
    case 'melanonychia':
      return <rect className="mark-dark" x="213" y="40" width="14" height="92" />
    case 'terrys_nails':
      return <rect className="mark-brown" x="188" y="118" width="64" height="14" />
    case 'lindsays_nails':
      return <rect className="mark-brown" x="188" y="86" width="64" height="46" />
    case 'onycholysis':
      return (
        <>
          <rect className="mark-white" x="188" y="108" width="64" height="24" />
          <path className="diagram-ray" d="M190 108 H250" />
        </>
      )
    case 'beaus_lines':
      return <rect className="mark-shadow" x="188" y="80" width="64" height="10" />
    case 'muehrckes_lines':
      return (
        <>
          <rect className="mark-white" x="188" y="64" width="64" height="7" />
          <rect className="mark-white" x="188" y="92" width="64" height="7" />
        </>
      )
    case 'splinter_hemorrhages':
      return (
        <>
          <rect className="mark-red" x="206" y="92" width="2.4" height="16" rx="1.2" />
          <rect className="mark-red" x="221" y="86" width="2.4" height="18" rx="1.2" />
          <rect className="mark-red" x="234" y="98" width="2.4" height="14" rx="1.2" />
        </>
      )
    case 'pitting':
      return (
        <>
          <circle className="mark-pit" cx="205" cy="66" r="3" />
          <circle className="mark-pit" cx="224" cy="72" r="3" />
          <circle className="mark-pit" cx="238" cy="90" r="3" />
          <circle className="mark-pit" cx="210" cy="96" r="3" />
          <circle className="mark-pit" cx="228" cy="110" r="3" />
          <circle className="mark-pit" cx="216" cy="118" r="3" />
        </>
      )
    case 'onychogryphosis':
      return (
        <>
          <rect className="mark-brown" x="188" y="96" width="64" height="36" />
          <rect className="mark-shadow" x="188" y="104" width="64" height="3" />
          <rect className="mark-shadow" x="188" y="114" width="64" height="3" />
          <rect className="mark-shadow" x="188" y="124" width="64" height="3" />
        </>
      )
    default:
      return null
  }
}

function NailPlate({ pattern, sub }) {
  const { t } = useI18n()
  const clip = `nailclip-${pattern}`
  const baseClass = PLATE_BASE[pattern] ?? 'plate-healthy'
  const subKey = `diagram.subs.${pattern}`
  const localizedSub = t(subKey)
  const label = sub ?? (localizedSub !== subKey ? localizedSub : t('diagram.fallbackSub'))

  return (
    <svg className="diagram" viewBox="0 0 296 182" role="img"
      aria-label={t('diagram.alt', { sub: label })}>
      <defs>
        <clipPath id={clip}>
          <rect x="188" y="40" width="64" height="92" rx="18" />
        </clipPath>
      </defs>

      {/* Typical */}
      <rect className="plate-healthy" x="44" y="40" width="64" height="92" rx="18" />
      <rect className="plate-stroke" x="44" y="40" width="64" height="92" rx="18" />
      <text className="diagram-cap" x="76" y="152" textAnchor="middle">{t('diagram.typical')}</text>
      <text className="diagram-sub" x="76" y="168" textAnchor="middle">{t('diagram.typicalSub')}</text>

      {/* Affected */}
      <rect className={baseClass} x="188" y="40" width="64" height="92" rx="18" />
      <g clipPath={`url(#${clip})`}>{plateOverlay(pattern)}</g>
      <rect className="plate-stroke" x="188" y="40" width="64" height="92" rx="18" />
      <text className="diagram-cap" x="220" y="152" textAnchor="middle">{t('diagram.sign')}</text>
      <text className="diagram-sub" x="220" y="168" textAnchor="middle">{label}</text>
    </svg>
  )
}

export default function NailDiagram({ type, sub }) {
  const { t } = useI18n()
  const img = COMPARISON_IMAGES[type]
  if (img) {
    return <img className="diagram" src={img} alt={t(`diagram.imgAlts.${type}`)} />
  }
  return <NailPlate pattern={type} sub={sub} />
}

/* ---- Annotated result diagram: every outside-range sign on one figure ---- */

// if more than one of these fires, just show the more specific one
const BASE_TINT_PRIORITY = ['cyanosis', 'pallor', 'terrys_nails', 'lindsays_nails']
const BASE_TINT_CLASS = {
  cyanosis: 'plate-blue',
  pallor: 'plate-pale',
  terrys_nails: 'plate-white',
  lindsays_nails: 'plate-white',
}

// legend swatch colors, matching each mark's actual fill
const SWATCH_COLOR = {
  clubbing: 'var(--warn)',
  koilonychia: 'var(--primary)',
  leukonychia: '#fbf7f3',
  melanonychia: '#463a32',
  pallor: '#e9e2dd',
  cyanosis: '#c6d2e0',
  terrys_nails: '#b67d5f',
  lindsays_nails: '#b67d5f',
  onycholysis: '#fbf7f3',
  beaus_lines: '#d6bdb1',
  muehrckes_lines: '#fbf7f3',
  splinter_hemorrhages: '#7d2b2b',
  pitting: '#caa893',
  onychogryphosis: '#b67d5f',
}

const PLATE_WITH_PROFILE_TRANSFORM = 'translate(-74.4,-22) scale(1.3)'
const PLATE_ALONE_TRANSFORM = 'translate(-180,-35) scale(1.5)'

function SideProfilePanel({ clubbing, koilonychia, t }) {
  // normal tapered tip, or a bulbous clubbed tip
  const skinPath = clubbing
    ? 'M40,20 C25,20 18,60 18,105 C18,150 20,175 55,182 C90,175 92,150 92,105 C92,60 85,20 70,20 Z'
    : 'M40,20 C25,20 20,60 20,100 C20,140 25,165 45,178 L65,178 C85,165 90,140 90,100 C90,60 85,20 70,20 Z'

  const nailPath = clubbing
    ? 'M70,20 Q95,60 93,105 Q90,160 55,182'
    : koilonychia
      ? 'M58,38 Q40,75 55,110 Q70,145 62,170'
      : 'M58,38 Q90,70 88,110 Q86,150 62,170'

  return (
    <g>
      <path className="diagram-skin" d={skinPath} />
      <path className="diagram-nail" d={nailPath} />
      {clubbing && (
        <>
          <path className="diagram-arc" d="M58,38 Q75,45 70,20" />
          <text className="diagram-tag diagram-tag--warn" x="135" y="18" textAnchor="end">{t('result.diagramClubbing')}</text>
        </>
      )}
      {koilonychia && (
        <>
          <circle className="diagram-drop" cx="55" cy="110" r="3" />
          <text className="diagram-tag" x="0" y="195">{t('result.diagramKoilonychia')}</text>
        </>
      )}
    </g>
  )
}

// one figure showing every outside-range sign from this scan
export function AnnotatedNailDiagram({ findings }) {
  const { t } = useI18n()
  const outside = (findings ?? []).filter((f) => f.verdict === 'outside')
  if (outside.length === 0) return null

  const clubbing = outside.some((f) => f.label === 'clubbing')
  const koilonychia = outside.some((f) => f.label === 'koilonychia')
  const hasProfile = clubbing || koilonychia
  const plateFindings = outside.filter((f) => f.label !== 'clubbing' && f.label !== 'koilonychia')
  const plateLabels = plateFindings.map((f) => f.label)

  const baseTintLabel = BASE_TINT_PRIORITY.find((l) => plateLabels.includes(l))
  const baseClass = baseTintLabel ? BASE_TINT_CLASS[baseTintLabel] : 'plate-healthy'
  const overlayMarks = plateLabels
    .map((label) => ({ label, mark: plateOverlay(label) }))
    .filter((m) => m.mark != null)

  const hasPlate = plateLabels.length > 0 || !hasProfile
  const plateTransform = hasProfile ? PLATE_WITH_PROFILE_TRANSFORM : PLATE_ALONE_TRANSFORM
  const clip = 'nailclip-annotated'

  return (
    <div className="annotated-diagram">
      <svg className="diagram" viewBox="0 0 300 220" role="img" aria-label={t('result.diagramOverviewAlt')}>
        <defs>
          <clipPath id={clip}>
            <rect x="188" y="40" width="64" height="92" rx="18" />
          </clipPath>
        </defs>
        {hasProfile && (
          <g transform="translate(10,10)">
            <SideProfilePanel clubbing={clubbing} koilonychia={koilonychia} t={t} />
          </g>
        )}
        {hasPlate && (
          <g transform={plateTransform}>
            <rect className={baseClass} x="188" y="40" width="64" height="92" rx="18" />
            <g clipPath={`url(#${clip})`}>
              {overlayMarks.map(({ label, mark }) => <g key={label}>{mark}</g>)}
            </g>
            <rect className="plate-stroke" x="188" y="40" width="64" height="92" rx="18" />
          </g>
        )}
      </svg>
      <ul className="annotated-diagram-legend">
        {outside.map((f) => (
          <li key={f.label}>
            <span className="annotated-diagram-swatch" style={{ background: SWATCH_COLOR[f.label] ?? 'var(--text-muted)' }} />
            {findingName(t, f)}
          </li>
        ))}
      </ul>
      <p className="annotated-diagram-note">{t('result.diagramOverviewNote')}</p>
    </div>
  )
}
