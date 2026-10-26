// "Save / print report" for the installed (Home Screen) app. iOS ignores window.print() in a standalone web app, so
// there the report is drawn onto page-sized images and handed to the share sheet, which offers Print, Save Image,
// Files, Mail and Messages. Canvas text uses the system fonts, so every language renders. Everywhere else the
// browser's own print dialog is used, with the print stylesheet in App.css.
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

const toFile = (canvas, name) =>
  new Promise((resolve) => canvas.toBlob((blob) => resolve(new File([blob], name, { type: 'image/png' })), 'image/png'))

export async function saveReport(t, lang, findings) {
  if (!isStandalone() || !navigator.canShare) {
    window.print()
    return
  }
  const pages = buildReportPages(t, lang, findings)
  const files = await Promise.all(pages.map((c, i) => toFile(c, `NailIQ-report-${i + 1}.png`)))
  if (!navigator.canShare({ files })) {
    window.print()
    return
  }
  try {
    await navigator.share({ files, title: t('result.reportTitle') })
  } catch (err) {
    if (err?.name !== 'AbortError') window.print()
  }
}
