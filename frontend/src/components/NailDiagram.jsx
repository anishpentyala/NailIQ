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

export default function NailDiagram({ type }) {
  if (type === 'clubbing') return <ClubbingDiagram />
  if (type === 'koilonychia') return <KoilonychiaDiagram />
  return null
}
