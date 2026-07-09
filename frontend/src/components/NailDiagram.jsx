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
import { useI18n } from '../i18n'

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
