const MESSAGES = {
  invalid_image: "That photo couldn't be processed. Please try again.",
  no_contour_found:
    "We couldn't find your finger in that photo. Make sure it fills the frame against a plain background.",
  contour_too_small:
    "Your finger looks too small in the frame. Move the camera closer and try again.",
  contour_degenerate:
    "That photo couldn't be processed. Please try again.",
  contour_touches_border:
    "Your finger is cut off at the edge of the frame. Recenter it and leave a little space around it.",
  fingertip_not_clear:
    "We couldn't get a clear view of your fingertip. Try better lighting and hold the camera steady.",
  cuticle_not_detected:
    "We couldn't find your nail and cuticle clearly. Make sure your whole nail is visible, nail facing the camera.",
  points_too_close:
    "We couldn't get a clear read on your nail shape. Try repositioning your finger and retaking the photo.",
  points_collinear:
    "We couldn't get a clear read on your nail shape. Try repositioning your finger and retaking the photo.",
  low_confidence:
    "The AI model wasn't confident enough about this photo to give a read. Try a clearer, well-lit shot of a single nail.",
}

const DEFAULT_MESSAGE =
  "We couldn't detect a nail in that photo. Try a plainer background, better lighting, and your whole finger in frame."

export function failureReasonMessage(failureReason) {
  return MESSAGES[failureReason] ?? DEFAULT_MESSAGE
}
