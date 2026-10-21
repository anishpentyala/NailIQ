const ONBOARDED_KEY = 'nailiq.onboarded'

export function hasOnboarded() {
  try {
    return localStorage.getItem(ONBOARDED_KEY) === '1'
  } catch {
    return false
  }
}

export function markOnboarded() {
  try {
    localStorage.setItem(ONBOARDED_KEY, '1')
  } catch {
    // storage unavailable: the intro just shows again next visit
  }
}
