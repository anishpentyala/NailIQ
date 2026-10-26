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

// A nail counts as present only when the real analysis located one: the engine returns overlay.top_bbox_norm
// only after it found a nail region that passed its own region-quality check. A blank, blurry or non-nail photo
// gets no region. Demo mode runs the real analysis first, so those photo checks still apply, and with no region the
// real "couldn't analyze" result is returned unchanged.
export function hasLocatedNail(data) {
  const box = data?.overlay?.top_bbox_norm
  const located = Array.isArray(box) && box.length === 4 && box.every((n) => typeof n === 'number')
  return located
}

export function applyDemoResult(data) {
  if (!hasLocatedNail(data)) return data
  return {
    ...data,
    demo: true,
    demo_label: DEMO_LABEL,
    findings: (data.findings ?? []).map((f) => ({ ...f, verdict: 'within', demo: true, failure_reason: null })),
  }
}
