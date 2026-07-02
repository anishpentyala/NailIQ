// Shared between HistoryView and HomeScreen so "what's the headline status of a
// scan" and "how long ago was that" are computed once, the same way, everywhere.

// One status for the whole scan: worst verdict wins, but it's still only ever
// within/outside/inconclusive -- never a named condition or a risk score.
export function overallStatus(findings) {
  const outsideCount = findings.filter((f) => f.verdict === 'outside').length
  if (outsideCount > 0) {
    return { verdict: 'outside', label: `${outsideCount} outside typical range` }
  }
  if (findings.some((f) => f.verdict === 'within')) {
    return { verdict: 'within', label: 'All within typical range' }
  }
  return { verdict: 'inconclusive', label: "Couldn't analyze this scan" }
}

export function relativeTime(isoString) {
  const minutes = Math.round((Date.now() - new Date(isoString).getTime()) / 60_000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days}d ago`
  return new Date(isoString).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
