// maps a backend failure reason code to the current language's message
export function failureReasonMessage(t, failureReason) {
  if (failureReason) {
    const key = `failure.${failureReason}`
    const message = t(key)
    if (message !== key) return message
  }
  return t('failure.default')
}
