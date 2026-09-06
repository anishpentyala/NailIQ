// Single source of truth for the on-screen alignment guide, in normalized
// (0..1) coordinates relative to the video frame. Mirrors the ring geometry in
// App.css's .cam-guide-ring / --landscape / --zoom rules -- if those CSS values
// change, update GUIDE_RECTS to match, so the box the user sees on screen is
// exactly the box CameraCapture.jsx crops to before sending.
//
// step === 'side' uses --landscape (width 70%, aspect-ratio 4/3 = width:height).
// step === 'top' uses --zoom (width 66%, aspect-ratio 3/4, inherited from the
// base .cam-guide-ring rule since --zoom only overrides width).
const GUIDE_RECTS = {
  side: { width: 0.7, aspect: 4 / 3 }, // width:height
  top: { width: 0.66, aspect: 3 / 4 },
}

// Extra room kept around the guide box's left/right/top edges before cropping,
// so a finger that's slightly misaligned with the ring isn't clipped by the
// crop itself. Rough starting estimate.
export const GUIDE_MARGIN_FRAC = 0.22

// {x, y, w, h} of the guide ring itself, normalized to the video frame and
// centered -- what's actually drawn on screen.
export function guideRect(step) {
  const { width, aspect } = GUIDE_RECTS[step] ?? GUIDE_RECTS.side
  const w = width
  const h = w / aspect
  return { x: (1 - w) / 2, y: (1 - h) / 2, w, h }
}

// The crop actually sent for analysis. Generous margin on left/right/top so a
// slightly-misaligned finger isn't clipped, but the BOTTOM always extends to
// the raw frame edge rather than being padded away.
//
// This asymmetry is deliberate, not an oversight: a real photo of your own
// finger always has your hand continuing out of frame at the bottom (you're
// holding your own hand up to the camera), regardless of which guide variant
// is showing. Letting that edge touch the frame border by construction is
// what preprocessing.py's border-entry detection needs to hand keypoints.py a
// reliable "which way is the fingertip" signal (see find_fingertip's
// entry_edge parameter) -- padding it away like a symmetric crop would
// re-loses that signal and silently falls back to the wrong-for-this-photo
// dataset-orientation default.
export function cropRect(step) {
  const g = guideRect(step)
  const mx = g.w * GUIDE_MARGIN_FRAC
  const my = g.h * GUIDE_MARGIN_FRAC
  const x = Math.max(0, g.x - mx)
  const y = Math.max(0, g.y - my)
  const w = Math.min(1 - x, g.w + 2 * mx)
  const h = 1 - y
  return { x, y, w, h }
}

// The video is displayed with CSS `object-fit: cover`, which scales it to
// fill the on-screen viewport while preserving aspect ratio, cropping
// whichever axis overflows. So a normalized rect in ON-SCREEN coordinates
// (what guideRect/cropRect describe) isn't simply proportional to the raw
// video frame's own pixel coordinates unless the two aspect ratios happen to
// match. This maps one to the other so the crop sent for analysis matches
// what the user actually saw inside the guide ring.
export function mapViewportRectToVideoRect(rect, viewportW, viewportH, videoW, videoH) {
  const viewportAspect = viewportW / viewportH
  const videoAspect = videoW / videoH

  let visW = 1
  let visH = 1
  let offX = 0
  let offY = 0
  if (videoAspect > viewportAspect) {
    // Video is relatively wider than the viewport -> its left/right are cropped.
    visW = viewportAspect / videoAspect
    offX = (1 - visW) / 2
  } else if (videoAspect < viewportAspect) {
    // Video is relatively taller -> its top/bottom are cropped.
    visH = videoAspect / viewportAspect
    offY = (1 - visH) / 2
  }

  return {
    x: offX + rect.x * visW,
    y: offY + rect.y * visH,
    w: rect.w * visW,
    h: rect.h * visH,
  }
}
