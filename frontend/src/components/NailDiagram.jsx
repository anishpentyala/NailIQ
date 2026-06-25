import clubbingComparisonImg from '../assets/diagrams/clubbing-comparison.png'
import koilonychiaComparisonImg from '../assets/diagrams/koilonychia-comparison.png'

function ClubbingDiagram() {
  return (
    <img className="diagram" src={clubbingComparisonImg}
      alt="Side-by-side comparison of a clubbed finger (enlarged bulbous tip, downward-curving nail, wider nail bed) versus a normal finger (tapered tip, flatter nail, narrower nail bed)" />
  )
}

function KoilonychiaDiagram() {
  return (
    <img className="diagram" src={koilonychiaComparisonImg}
      alt="Side-by-side comparison of normal nails (flat or gently domed, convex cross-section) versus koilonychia (spoon-shaped nails that dip concave in the middle)" />
  )
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

const PLATE_SUB = {
  leukonychia: 'white spots',
  melanonychia: 'dark band',
  pallor: 'pale',
  cyanosis: 'bluish',
  terrys_nails: 'white, dark tip',
  lindsays_nails: 'half & half',
  onycholysis: 'tip lifted',
  beaus_lines: 'groove across',
  muehrckes_lines: 'white bands',
  splinter_hemorrhages: 'tiny streaks',
  pitting: 'small pits',
}

function NailPlate({ pattern, sub }) {
  const clip = `nailclip-${pattern}`
  const baseClass = PLATE_BASE[pattern] ?? 'plate-healthy'
  const label = sub ?? PLATE_SUB[pattern] ?? 'a sign'

  return (
    <svg className="diagram" viewBox="0 0 296 182" role="img"
      aria-label={`Top view of a typical nail versus one showing ${sub}`}>
      <defs>
        <clipPath id={clip}>
          <rect x="188" y="40" width="64" height="92" rx="18" />
        </clipPath>
      </defs>

      {/* Typical */}
      <rect className="plate-healthy" x="44" y="40" width="64" height="92" rx="18" />
      <rect className="plate-stroke" x="44" y="40" width="64" height="92" rx="18" />
      <text className="diagram-cap" x="76" y="152" textAnchor="middle">Typical</text>
      <text className="diagram-sub" x="76" y="168" textAnchor="middle">even, smooth</text>

      {/* Affected */}
      <rect className={baseClass} x="188" y="40" width="64" height="92" rx="18" />
      <g clipPath={`url(#${clip})`}>{plateOverlay(pattern)}</g>
      <rect className="plate-stroke" x="188" y="40" width="64" height="92" rx="18" />
      <text className="diagram-cap" x="220" y="152" textAnchor="middle">Sign</text>
      <text className="diagram-sub" x="220" y="168" textAnchor="middle">{label}</text>
    </svg>
  )
}

export default function NailDiagram({ type, sub }) {
  if (type === 'clubbing') return <ClubbingDiagram />
  if (type === 'koilonychia') return <KoilonychiaDiagram />
  return <NailPlate pattern={type} sub={sub} />
}
