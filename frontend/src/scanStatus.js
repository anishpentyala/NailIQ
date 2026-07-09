// Shared between HistoryView and HomeScreen so "what's the headline status of a
// scan" and "how long ago was that" are computed once, the same way, everywhere.
// Both take `t` (and relativeTime the lang) so the output follows the UI language.

// One status for the whole scan: worst verdict wins, but it's still only ever
// within/outside/inconclusive -- never a named condition or a risk score.
export function overallStatus(findings, t) {
  const outsideCount = findings.filter((f) => f.verdict === 'outside').length
  if (outsideCount > 0) {
    return { verdict: 'outside', label: t('status.outsideCount', { n: outsideCount }) }
  }
  if (findings.some((f) => f.verdict === 'within')) {
    return { verdict: 'within', label: t('status.allWithin') }
  }
  return { verdict: 'inconclusive', label: t('status.cantAnalyze') }
}

export function relativeTime(isoString, t, lang) {
  const minutes = Math.round((Date.now() - new Date(isoString).getTime()) / 60_000)
  if (minutes < 1) return t('time.justNow')
  if (minutes < 60) return t('time.minutesAgo', { n: minutes })
  const hours = Math.round(minutes / 60)
  if (hours < 24) return t('time.hoursAgo', { n: hours })
  const days = Math.round(hours / 24)
  if (days === 1) return t('time.yesterday')
  if (days < 7) return t('time.daysAgo', { n: days })
  return new Date(isoString).toLocaleDateString(lang, { month: 'short', day: 'numeric' })
}
