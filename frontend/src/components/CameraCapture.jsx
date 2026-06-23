import { useRef, useState, useCallback } from 'react'
import Webcam from 'react-webcam'
import { validatePhoto } from '../api'
import { failureReasonMessage } from '../failureReasons'

const VIDEO_CONSTRAINTS = {
  facingMode: 'environment',
}

const STEPS = {
  side: {
    instructions:
      'Hold your finger sideways (profile view) against a plain background, nail facing the camera, fingertip pointing toward the bottom of the frame.',
    buttonLabel: 'Capture side profile',
  },
  top: {
    instructions:
      'Now lay your finger flat and photograph it from above, nail facing the camera, against a plain background.',
    buttonLabel: 'Capture top-down view',
  },
}

export default function CameraCapture({ onCapture, loading }) {
  const webcamRef = useRef(null)
  const [step, setStep] = useState('side')
  const [sideImage, setSideImage] = useState(null)
  const [cameraError, setCameraError] = useState(null)
  const [validating, setValidating] = useState(false)
  const [retakeError, setRetakeError] = useState(null)

  const handleCapture = useCallback(async () => {
    const screenshot = webcamRef.current?.getScreenshot()
    if (!screenshot) {
      setCameraError("Couldn't capture an image. Make sure your camera is allowed and try again.")
      return
    }
    const base64 = screenshot.split(',')[1]

    setRetakeError(null)
    setValidating(true)
    let validation
    try {
      validation = await validatePhoto(base64, step)
    } catch (err) {
      setValidating(false)
      setRetakeError("Couldn't check that photo. Is the backend running?")
      return
    }
    setValidating(false)

    if (!validation.ok) {
      setRetakeError(failureReasonMessage(validation.failure_reason))
      return
    }

    if (step === 'side') {
      setSideImage(base64)
      setStep('top')
    } else {
      onCapture({ sideImage, topImage: base64 })
    }
  }, [step, sideImage, onCapture])

  const { instructions, buttonLabel } = STEPS[step]

  return (
    <div className="capture-card">
      <p className="capture-step">Step {step === 'side' ? '1' : '2'} of 2</p>
      <p className="capture-instructions">{instructions}</p>

      {retakeError && <div className="camera-error">{retakeError}</div>}

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
        disabled={loading || validating || !!cameraError}
      >
        {validating ? 'Checking photo…' : loading ? 'Analyzing…' : buttonLabel}
      </button>
    </div>
  )
}
