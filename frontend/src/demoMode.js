// Demo mode for the school project. When on, a scan that has a readable nail in the photo returns a fixed
// "within typical range" result for every sign instead of the real analysis. Every demo result carries the label
// below on screen, in the saved report and in anything exported. Demo mode is off by default and turning it off
// returns the app to the real scanner. Nothing here changes the scanner itself.
export const DEMO_LABEL = 'Demo result, not a medical assessment'
const KEY = 'nailiq.demoMode'

export function isDemoMode() {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

export function setDemoMode(on) {
  try {
    if (on) localStorage.setItem(KEY, '1')
    else localStorage.removeItem(KEY)
  } catch {
    /* storage blocked: demo mode stays off */
  }
}

// Runs the real analysis first (so the photo checks and nail detection still apply), then, only if at least one
// sign could be read from a nail in the photo, reports every sign as within typical range. If no sign could be
// read (no nail found / unusable photo) the real "couldn't analyze" result is returned unchanged.
export function applyDemoResult(data) {
  const findings = data?.findings ?? []
  if (!findings.some((f) => f.verdict !== 'inconclusive')) return data
  return {
    ...data,
    demo: true,
    demo_label: DEMO_LABEL,
    findings: findings.map((f) => ({ ...f, verdict: 'within', demo: true, failure_reason: null })),
  }
}
