import { useRef, useState } from 'react'
import { useI18n } from '../i18n'

const LIMIT = 0.05
const DEFAULT_BOX = [0.36, 0.14, 0.64, 0.42]
const TOO_BIG_AREA = 0.18 // share of the photo; a nail rarely fills more than this
const clamp = (value, low, high) => Math.max(low, Math.min(high, value))

export default function NailBoxSelector({ image, initialBox, busy, error, onConfirm, onRetake }) {
  const { t } = useI18n()
  // Without a detected nail, start with a small box where the nail sits inside the camera guide (near the top of the
  // ring, centred) rather than a half-photo box that swallows the whole finger.
  const [box, setBox] = useState(initialBox ?? DEFAULT_BOX)
  const [aspect, setAspect] = useState(1)
  const frame = useRef(null)
  const drag = useRef(null)

  function move(mode, original, dx, dy) {
    const [x0, y0, x1, y1] = original
    if (mode === 'move') {
      dx = clamp(dx, -x0, 1 - x1)
      dy = clamp(dy, -y0, 1 - y1)
      return [x0 + dx, y0 + dy, x1 + dx, y1 + dy]
    }
    return [
      mode.includes('w') ? clamp(x0 + dx, 0, x1 - LIMIT) : x0,
      mode.includes('n') ? clamp(y0 + dy, 0, y1 - LIMIT) : y0,
      mode.includes('e') ? clamp(x1 + dx, x0 + LIMIT, 1) : x1,
      mode.includes('s') ? clamp(y1 + dy, y0 + LIMIT, 1) : y1,
    ]
  }

  function start(event, mode) {
    if (busy) return
    event.preventDefault()
    event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    drag.current = { mode, box, x: event.clientX, y: event.clientY }
  }

  function update(event) {
    if (!drag.current || busy) return
    const rect = frame.current.getBoundingClientRect()
    const origin = drag.current
    setBox(move(origin.mode, origin.box,
      (event.clientX - origin.x) / rect.width, (event.clientY - origin.y) / rect.height))
  }

  function keyboard(event, mode) {
    const delta = { ArrowLeft: [-0.01, 0], ArrowRight: [0.01, 0], ArrowUp: [0, -0.01], ArrowDown: [0, 0.01] }[event.key]
    if (!delta || busy) return
    event.preventDefault()
    setBox((current) => move(mode, current, ...delta))
  }

  return (
    <section className="nail-crop-review" aria-label={t('crop.title')}>
      <h2>{t('crop.title')}</h2>
      <p>{t('crop.instructions')}</p>
      <div className="nail-crop-frame" ref={frame} style={{ width: `min(100%, ${58 * aspect}dvh)` }}>
        <img src={`data:image/jpeg;base64,${image}`} alt={t('crop.photo')}
          draggable={false} onLoad={(event) => setAspect(event.currentTarget.naturalWidth / event.currentTarget.naturalHeight)} />
        <div className="nail-crop-box" style={{ left: `${box[0] * 100}%`, top: `${box[1] * 100}%`,
          width: `${(box[2] - box[0]) * 100}%`, height: `${(box[3] - box[1]) * 100}%` }}>
          <button className="nail-crop-move" type="button" aria-label={t('crop.move')} disabled={busy}
            onPointerDown={(event) => start(event, 'move')} onPointerMove={update}
            onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}
            onKeyDown={(event) => keyboard(event, 'move')} />
          {['nw', 'ne', 'sw', 'se'].map((corner) => (
            <button key={corner} className={`nail-crop-handle nail-crop-handle--${corner}`}
              type="button" aria-label={t(`crop.${corner}`)} disabled={busy}
              onPointerDown={(event) => start(event, corner)} onPointerMove={update}
              onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}
              onKeyDown={(event) => keyboard(event, corner)} />
          ))}
        </div>
      </div>
      {(box[2] - box[0]) * (box[3] - box[1]) > TOO_BIG_AREA && <p className="nail-crop-hint" role="status">{t('crop.tooBig')}</p>}
      {error && <p className="camera-error" role="alert">{error}</p>}
      <div className="nail-crop-actions">
        <button type="button" disabled={busy} onClick={() => onConfirm(box)}>{busy ? t('camera.checking') : t('crop.confirm')}</button>
        <button type="button" disabled={busy} onClick={onRetake}>{t('crop.retake')}</button>
      </div>
    </section>
  )
}
