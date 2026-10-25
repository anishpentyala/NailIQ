// Scan history kept on this device (localStorage) when the AI runs on-device, so nothing is stored on a server.

const KEY = 'nailiq.history.v1'
const FEEDBACK_KEY = 'nailiq.feedback.v1'
const MAX_SCANS = 100

function read(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

function write(key, rows) {
  // storage can be full or blocked; drop the oldest rows until it fits, and give up quietly if it never does
  let keep = rows.length
  for (;;) {
    try {
      localStorage.setItem(key, JSON.stringify(rows.slice(0, keep)))
      return
    } catch {
      if (keep === 0) return
      keep = Math.floor(keep / 2)
    }
  }
}

export function saveLocalScan(findings) {
  const scans = read(KEY)
  const record = { id: Date.now(), created_at: new Date().toISOString(), findings }
  write(KEY, [record, ...scans].slice(0, MAX_SCANS))
  return record
}

export function listLocalScans(limit) {
  return read(KEY).slice(0, limit || MAX_SCANS)
}

export function clearLocalScans() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    /* storage blocked: nothing was saved */
  }
}

export function saveLocalFeedback(row) {
  write(FEEDBACK_KEY, [{ ...row, created_at: new Date().toISOString() }, ...read(FEEDBACK_KEY)].slice(0, 500))
}
