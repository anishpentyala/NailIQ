"""Generates the NailIQ logo files (SVG) into this folder. No fonts: the wordmark is drawn from strokes.

Concept: a viewfinder (scan) around a fingernail with its lunula and a glowing scan point - the "i" dot of the
wordmark is the same point. Run: python brand/make_brand.py  (then render PNGs with brand/render_png.cjs if wanted).
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent

TEAL = "#3ddbb3"
TEAL_DEEP = "#1f9d82"
INK = "#0b0c0e"
PAPER = "#f2f4f4"


def mark_group(nail_stroke, nail_fill_top, nail_fill_bot, corner, dot, lunula, uid, corners=True):
    """The 120x120 mark (no background). Colours differ for dark/light backgrounds."""
    corner_svg = f'''<g fill="none" stroke="url(#{uid}c)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 32V19a12 12 0 0 1 12-12h13"/><path d="M88 7h13a12 12 0 0 1 12 12v13"/><path d="M113 88v13a12 12 0 0 1-12 12H88"/><path d="M32 113H19a12 12 0 0 1-12-12V88"/></g>''' if corners else ''
    return f'''
  <defs>
    <linearGradient id="{uid}c" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{TEAL}"/><stop offset="1" stop-color="{TEAL_DEEP}"/></linearGradient>
    <linearGradient id="{uid}n" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{nail_fill_top}"/><stop offset="1" stop-color="{nail_fill_bot}"/></linearGradient>
    <radialGradient id="{uid}g"><stop offset="0" stop-color="{TEAL}" stop-opacity="0.9"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>
    <clipPath id="{uid}k"><path d="M33 52C33 34 45 24 60 24S87 34 87 52V78C87 90 75 98 60 98S33 90 33 78Z"/></clipPath>
  </defs>
  {corner_svg}
  <path d="M33 52C33 34 45 24 60 24S87 34 87 52V78C87 90 75 98 60 98S33 90 33 78Z" fill="url(#{uid}n)" stroke="{nail_stroke}" stroke-width="4.5" stroke-linejoin="round"/>
  <g clip-path="url(#{uid}k)"><ellipse cx="60" cy="101" rx="25" ry="15" fill="{lunula}" opacity="0.92"/></g>
  <circle cx="68" cy="47" r="15" fill="url(#{uid}g)"/>
  <circle cx="68" cy="47" r="5" fill="{dot}"/>
'''


def wordmark_group(color):
    """Monoline 'NailIQ' (cap height 56, baseline y=70). The i-dot and Q tail are the brand teal."""
    return f'''
  <g fill="none" stroke="{color}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 70V14L38 70V14"/>
    <circle cx="62" cy="51" r="16.5"/><path d="M78.5 34V70"/>
    <path d="M97 34V70"/>
    <path d="M113 14V70"/>
    <path d="M127 14h16M135 14V70M127 70h16"/>
    <circle cx="172" cy="42" r="28"/>
  </g>
  <circle cx="97" cy="18" r="5.2" fill="{TEAL}"/>
  <path d="M184 56L199 76" fill="none" stroke="{TEAL}" stroke-width="7" stroke-linecap="round"/>
'''


def svg(w, h, body, bg=None, extra=""):
    bgrect = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="NailIQ">{extra}{bgrect}{body}</svg>\n'


DARK = dict(nail_stroke="#f2d3c8", nail_fill_top="#f6d5ca", nail_fill_bot="#e3978c", corner=TEAL, dot="#ffffff", lunula="#fbe9e2")
LIGHT = dict(nail_stroke="#0f6b58", nail_fill_top="#f4d6cc", nail_fill_bot="#e8a79c", corner=TEAL_DEEP, dot="#ffffff", lunula="#fdeee8")


def write(name, content):
    (OUT / name).write_text(content, encoding="utf-8")


def main():
    # marks
    write("logo-mark.svg", svg(120, 120, mark_group(uid="d", **DARK)))
    write("logo-mark-light.svg", svg(120, 120, mark_group(uid="l", **LIGHT)))

    # horizontal lockups: mark + wordmark
    for name, pal, ink, uid in (("logo-lockup.svg", DARK, PAPER, "ld"), ("logo-lockup-light.svg", LIGHT, INK, "ll")):
        body = f'<g>{mark_group(uid=uid, **pal)}</g><g transform="translate(138 14)">{wordmark_group(ink)}</g>'
        write(name, svg(352, 120, body))

    # app icon: rounded square, dark teal glow, mark centred
    icon_bg = '''<defs><radialGradient id="ib" cx="0.5" cy="0.35" r="0.85"><stop offset="0" stop-color="#1d3a33"/><stop offset="1" stop-color="#0b0c0e"/></radialGradient></defs>
<rect width="1024" height="1024" rx="228" fill="url(#ib)"/>'''
    write("app-icon.svg", svg(1024, 1024, f'{icon_bg}<g transform="translate(192 192) scale(5.33)">{mark_group(uid="ai", **DARK)}</g>'))

    # favicon: same icon at small size reads better without the corner brackets' thin gaps, so keep the full mark
    write("favicon.svg", svg(120, 120, f'<rect width="120" height="120" rx="28" fill="#0b0c0e"/><g transform="translate(60 61) scale(1.28) translate(-60 -61)">{mark_group(uid="fv", corners=False, **DARK)}</g>'))
    print("wrote svgs to", OUT)


if __name__ == "__main__":
    main()
