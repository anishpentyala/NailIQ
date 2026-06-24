function ClubbingDiagram() {
  return (
    <svg className="diagram" viewBox="0 0 340 190" role="img"
      aria-label="Side view of a typical fingertip versus a clubbed fingertip">
      {/* ---- Typical ---- */}
      <path className="diagram-skin"
        d="M25 130 L25 96 L100 86 L150 102 Q164 110 150 122 L25 130 Z" />
      <path className="diagram-nail" d="M100 86 L150 102" />
      {/* angle rays */}
      <path className="diagram-ray" d="M100 86 L42 93" />
      <path className="diagram-ray" d="M100 86 L160 102" />
      <path className="diagram-arc" d="M72 90 Q104 96 132 99" />
      <text className="diagram-angle diagram-angle--ok" x="100" y="74" textAnchor="middle">≈160°</text>
      <text className="diagram-cap" x="92" y="150" textAnchor="middle">Typical</text>
      <text className="diagram-sub" x="92" y="166" textAnchor="middle">clear dip, flat nail</text>

      {/* ---- Clubbed ---- */}
      <path className="diagram-skin"
        d="M190 130 L190 96 L250 90 Q284 84 304 100 Q320 112 302 122 Q280 128 250 126 L190 130 Z" />
      <path className="diagram-nail" d="M252 89 Q284 85 306 101" />
      <path className="diagram-ray" d="M252 89 L196 95" />
      <path className="diagram-ray" d="M252 89 L312 90" />
      <path className="diagram-arc" d="M224 92 Q256 88 300 91" />
      <text className="diagram-angle diagram-angle--warn" x="252" y="76" textAnchor="middle">&gt;180°</text>
      <text className="diagram-cap" x="256" y="152" textAnchor="middle">Clubbed</text>
      <text className="diagram-sub" x="256" y="168" textAnchor="middle">rounded, bulging tip</text>
    </svg>
  )
}

function KoilonychiaDiagram() {
  return (
    <svg className="diagram" viewBox="0 0 340 190" role="img"
      aria-label="End-on view of a typical nail versus a spoon-shaped nail">
      {/* ---- Typical (gently domed) ---- */}
      <path className="diagram-skin"
        d="M30 78 Q92 54 154 78 Q154 104 92 110 Q30 104 30 78 Z" />
      <path className="diagram-nail" d="M30 78 Q92 56 154 78" />
      <text className="diagram-cap" x="92" y="140" textAnchor="middle">Typical</text>
      <text className="diagram-sub" x="92" y="156" textAnchor="middle">flat or gently domed</text>

      {/* ---- Spoon (concave) ---- */}
      <path className="diagram-skin"
        d="M192 62 Q254 102 316 62 Q316 96 254 104 Q192 96 192 62 Z" />
      <path className="diagram-nail" d="M192 62 Q254 100 316 62" />
      {/* water drop sitting in the dip */}
      <path className="diagram-drop" d="M254 74 c-7 9 -7 16 0 16 c7 0 7 -7 0 -16 Z" />
      {/* depth indicator */}
      <path className="diagram-ray" d="M192 62 L316 62" />
      <path className="diagram-dim" d="M254 63 L254 99" />
      <text className="diagram-cap" x="254" y="140" textAnchor="middle">Spoon</text>
      <text className="diagram-sub" x="254" y="156" textAnchor="middle">dips in the middle</text>
    </svg>
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
