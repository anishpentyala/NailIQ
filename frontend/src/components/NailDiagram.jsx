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

function LeukonychiaDiagram() {
  return (
    <img className="diagram" src={leukonychiaComparisonImg}
      alt="Side-by-side comparison of normal nails versus leukonychia (scattered punctate white spots across the nail plate)" />
  )
}

function MelanonychiaDiagram() {
  return (
    <img className="diagram" src={melanonychiaComparisonImg}
      alt="Side-by-side comparison of normal nails versus melanonychia (a single dark brown-black longitudinal band running down the nail plate)" />
  )
}

function PallorDiagram() {
  return (
    <img className="diagram" src={pallorComparisonImg}
      alt="Side-by-side comparison of a normal pink nail bed versus pallor (a pale, washed-out nail bed)" />
  )
}

function CyanosisDiagram() {
  return (
    <img className="diagram" src={cyanosisComparisonImg}
      alt="Side-by-side comparison of a normal pink nail bed versus cyanosis (a bluish, dusky nail bed)" />
  )
}

function TerrysNailsDiagram() {
  return (
    <img className="diagram" src={terrysNailsComparisonImg}
      alt="Side-by-side comparison of normal nails versus Terry's nails (a mostly white, opaque nail plate with a narrow dark band at the tip)" />
  )
}

function LindsaysNailsDiagram() {
  return (
    <img className="diagram" src={lindsaysNailsComparisonImg}
      alt="Side-by-side comparison of normal nails versus Lindsay's (half-and-half) nails (a dull-white proximal half and a darker pink-brown distal half with a sharp dividing line)" />
  )
}

function OnycholysisDiagram() {
  return (
    <img className="diagram" src={onycholysisComparisonImg}
      alt="Side-by-side comparison of normal nails versus onycholysis (the nail plate separating and lifting from the nail bed at the distal free edge, leaving a white or yellow-white detached area)" />
  )
}

function BeausLinesDiagram() {
  return (
    <img className="diagram" src={beausLinesComparisonImg}
      alt="Side-by-side comparison of normal nails versus Beau's lines (a transverse groove or depression running across the nail plate)" />
  )
}

function MuehrckesLinesDiagram() {
  return (
    <img className="diagram" src={muehrckesLinesComparisonImg}
      alt="Side-by-side comparison of normal nails versus Muehrcke's lines (a pair of transverse white bands running across the nail plate)" />
  )
}

function SplinterHemorrhagesDiagram() {
  return (
    <img className="diagram" src={splinterHemorrhagesComparisonImg}
      alt="Comparison of normal nails versus typical and severe splinter hemorrhages (small, thin, reddish-brown vertical lines under the nail)" />
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
  if (type === 'leukonychia') return <LeukonychiaDiagram />
  if (type === 'melanonychia') return <MelanonychiaDiagram />
  if (type === 'pallor') return <PallorDiagram />
  if (type === 'cyanosis') return <CyanosisDiagram />
  if (type === 'terrys_nails') return <TerrysNailsDiagram />
  if (type === 'lindsays_nails') return <LindsaysNailsDiagram />
  if (type === 'onycholysis') return <OnycholysisDiagram />
  if (type === 'beaus_lines') return <BeausLinesDiagram />
  if (type === 'muehrckes_lines') return <MuehrckesLinesDiagram />
  if (type === 'splinter_hemorrhages') return <SplinterHemorrhagesDiagram />
  return <NailPlate pattern={type} sub={sub} />
}
