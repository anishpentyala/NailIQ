import { useRef, useState, useCallback } from 'react'
import Webcam from 'react-webcam'

const VIDEO_CONSTRAINTS = {
  facingMode: 'environment',
}

export default function CameraCapture({ onCapture, loading }) {
  const webcamRef = useRef(null)
  const [cameraError, setCameraError] = useState(null)

  const handleCapture = useCallback(() => {
    const screenshot = webcamRef.current?.getScreenshot()
    if (!screenshot) {
      setCameraError("Couldn't capture an image. Make sure your camera is allowed and try again.")
      return
    }
    const base64 = screenshot.split(',')[1]
    onCapture(base64)
  }, [onCapture])

  return (
    <div className="capture-card">
      <p className="capture-instructions">
        Hold your finger sideways (profile view) against a plain background, with the
        nail facing the camera. Good lighting helps.
      </p>

      <div className="webcam-frame">
        {cameraError ? (
          <div className="camera-error">{cameraError}</div>
        ) : (
          <>
            <Webcam
              ref={webcamRef}
              audio={false}
              screenshotFormat="image/jpeg"
              videoConstraints={VIDEO_CONSTRAINTS}
              onUserMediaError={() =>
                setCameraError(
                  'Camera access was blocked or unavailable. Check your browser permissions and reload.'
                )
              }
            />
            <div className="webcam-guide" />
          </>
        )}
      </div>

      <button
        type="button"
        className="primary-btn"
        onClick={handleCapture}
        disabled={loading || !!cameraError}
      >
        {loading ? 'Analyzing…' : 'Capture & Analyze'}
      </button>
    </div>
  )
}
