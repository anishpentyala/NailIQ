// "Save / print report": draws the report onto A4 pages with canvas and turns them into a PDF. iOS ignores
// window.print() in a Home Screen app, so a PDF is the one format that works there and in every browser. Canvas
// text uses the system fonts, so every language renders.
import { failureReasonMessage } from './failureReasons'
import { findingName } from './i18n'

const W = 1240 // A4 at 150 dpi
const H = 1754
const M = 110 // page margin
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", sans-serif'
const COLOR = { within: '#1f7a5c', outside: '#a3620a', inconclusive: '#5b6366', text: '#14191b', muted: '#5b6366' }

function isStandalone() {
  return window.navigator.standalone === true || window.matchMedia?.('(display-mode: standalone)').matches === true
}

function summaryText(t, findings) {
  const outside = findings.filter((f) => f.verdict === 'outside').length
  const inconclusive = findings.filter((f) => f.verdict === 'inconclusive').length
  if (outside === 1) return t('result.summaryOutsideOne')
  if (outside > 1) return t('result.summaryOutside', { n: outside })
  if (inconclusive > 0 && inconclusive === findings.length) return t('result.summaryInconclusive')
  return t('result.summaryWithin')
}

// Splits text into lines that fit maxWidth: words break at spaces, CJK characters can break anywhere, and a word
// too long for a line is split by character.
const TOKEN = /\s+|[⺀-鿿豈-﫿＀-￯]|[^\s⺀-鿿豈-﫿＀-￯]+/g

function wrap(ctx, text, maxWidth) {
  const units = (text.match(TOKEN) ?? []).flatMap((u) => (ctx.measureText(u).width > maxWidth ? Array.from(u) : [u]))
  const lines = []
  let line = ''
  for (const unit of units) {
    const next = line + unit
    if (ctx.measureText(next).width > maxWidth && line.trim()) {
      lines.push(line.trimEnd())
      line = unit.trimStart()
    } else {
      line = next
    }
  }
  if (line.trim()) lines.push(line.trimEnd())
  return lines
}

export function buildReportPages(t, lang, findings) {
  const pages = []
  let ctx = null
  let y = 0

  const newPage = () => {
    const canvas = document.createElement('canvas')
    canvas.width = W
    canvas.height = H
    ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, W, H)
    ctx.textBaseline = 'top'
    pages.push(canvas)
    y = M
  }

  const write = (text, { size = 30, weight = 400, color = COLOR.text, gap = 10, lineHeight = 1.35 } = {}) => {
    ctx.font = `${weight} ${size}px ${FONT}`
    for (const line of wrap(ctx, text, W - 2 * M)) {
      if (y + size * lineHeight > H - M) {
        newPage()
        ctx.font = `${weight} ${size}px ${FONT}`
      }
      ctx.fillStyle = color
      ctx.fillText(line, M, y)
      y += size * lineHeight
    }
    y += gap
  }

  const rule = () => {
    if (y + 30 > H - M) newPage()
    ctx.fillStyle = '#d9dede'
    ctx.fillRect(M, y + 8, W - 2 * M, 2)
    y += 30
  }

  newPage()
  write(t('result.reportTitle'), { size: 46, weight: 700, gap: 6 })
  write(new Date().toLocaleDateString(lang, { year: 'numeric', month: 'long', day: 'numeric' }),
    { size: 28, color: COLOR.muted, gap: 24 })
  write(summaryText(t, findings), { size: 34, weight: 600, gap: 20 })
  rule()

  for (const f of findings) {
    const message = f.verdict === 'inconclusive'
      ? failureReasonMessage(t, f.failure_reason)
      : t(`verdict.${f.verdict}.message`)
    write(findingName(t, f), { size: 32, weight: 600, gap: 4 })
    write(t(`verdict.${f.verdict}.label`), { size: 28, weight: 600, color: COLOR[f.verdict] ?? COLOR.text, gap: 4 })
    write(message, { size: 26, color: COLOR.muted, gap: 8 })
    rule()
  }

  write(t('result.disclaimer'), { size: 24, color: COLOR.muted, gap: 12 })
  write(t('result.sources'), { size: 22, color: COLOR.muted, gap: 0 })
  return pages
}

// A minimal PDF: one A4 page per canvas, each page a full-page JPEG image (DCTDecode). Built by hand so the app
// needs no PDF library.
export function pagesToPdf(pages) {
  const enc = new TextEncoder()
  const parts = []
  const offsets = []
  let length = 0
  const push = (chunk) => {
    const bytes = typeof chunk === 'string' ? enc.encode(chunk) : chunk
    parts.push(bytes)
    length += bytes.length
  }
  const object = (id, ...chunks) => {
    offsets[id] = length
    push(`${id} 0 obj\n`)
    chunks.forEach(push)
    push('\nendobj\n')
  }
  const pw = 595.28 // A4 in points
  const ph = 841.89
  const pageIds = pages.map((_, i) => 3 + i * 3)

  push('%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')
  object(1, '<< /Type /Catalog /Pages 2 0 R >>')
  object(2, `<< /Type /Pages /Kids [${pageIds.map((id) => `${id} 0 R`).join(' ')}] /Count ${pages.length} >>`)
  pages.forEach((canvas, i) => {
    const id = pageIds[i]
    const jpeg = Uint8Array.from(atob(canvas.toDataURL('image/jpeg', 0.92).split(',')[1]), (c) => c.charCodeAt(0))
    const draw = `q ${pw} 0 0 ${ph} 0 0 cm /Im0 Do Q`
    object(id, `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pw} ${ph}] /Resources << /XObject << /Im0 ${id + 2} 0 R >> >> /Contents ${id + 1} 0 R >>`)
    object(id + 1, `<< /Length ${draw.length} >>\nstream\n${draw}\nendstream`)
    object(id + 2, `<< /Type /XObject /Subtype /Image /Width ${canvas.width} /Height ${canvas.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`, jpeg, '\nendstream')
  })
  const count = 3 + pages.length * 3
  const xref = length
  push(`xref\n0 ${count}\n0000000000 65535 f \n`)
  for (let id = 1; id < count; id++) push(`${String(offsets[id]).padStart(10, '0')} 00000 n \n`)
  push(`trailer\n<< /Size ${count} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`)
  const bytes = new Uint8Array(length)
  let at = 0
  for (const part of parts) {
    bytes.set(part, at)
    at += part.length
  }
  return bytes
}

function download(file) {
  const url = URL.createObjectURL(file)
  const link = document.createElement('a')
  link.download = file.name
  link.href = url
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

// Saves the report as a PDF. A browser downloads it straight away. iOS Home Screen apps can't download a file the
// page made itself (taps on a download link are silently ignored, and opening the file replaces the app with a
// screen it can't leave), so there the report opens in an in-app preview instead (onPreview gets the page images and
// the PDF file), and its Save PDF button hands the file to iOS, whose sheet offers Save to Files and Print.
export function saveReport(t, lang, findings, onPreview) {
  let pages
  let file
  try {
    pages = buildReportPages(t, lang, findings)
    const name = `NailIQ-report-${new Date().toLocaleDateString('en-CA')}.pdf` // en-CA is YYYY-MM-DD, local date
    file = new File([pagesToPdf(pages)], name, { type: 'application/pdf' })
  } catch {
    window.print()
    return
  }
  if (isStandalone() && onPreview) onPreview({ images: pages.map((c) => c.toDataURL('image/jpeg', 0.9)), file })
  else download(file)
}

export async function savePdfFile(file) {
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file] })
    } catch {
      // the person closed the sheet
    }
  } else {
    download(file)
  }
}
