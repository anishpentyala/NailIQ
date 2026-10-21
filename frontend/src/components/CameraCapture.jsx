import { useRef, useState, useCallback } from 'react'
import Webcam from 'react-webcam'
import NailBoxSelector from './NailBoxSelector'
import { validatePhoto } from '../api'
import { failureReasonMessage } from '../failureReasons'
import { useI18n } from '../i18n'
import { cropRect, mapViewportRectToVideoRect } from '../cameraGuide'
import cameraGuideSide from '../assets/camera-guide-side.png'
import cameraGuideTop from '../assets/camera-guide-top.png'

// shows a faint finger outline inside the guide ring so people know what shape to line up
function FrameGuideSilhouette({ step }) {
  return (
    <img
      className="cam-guide-silhouette cam-guide-silhouette--image"
      src={step === 'side' ? cameraGuideSide : cameraGuideTop}
      alt=""
      aria-hidden="true"
    />
  )
}

export default function CameraCapture({ onCapture, loading, onClose }) {
  const { t } = useI18n()
  const webcamRef = useRef(null)
  const fileInputRef = useRef(null)
  const [step, setStep] = useState('side')
  const [sideImage, setSideImage] = useState(null)
  const [cameraError, setCameraError] = useState(null)
  const [validating, setValidating] = useState(false)
  const [retakeError, setRetakeError] = useState(null)
  const [flashActive, setFlashActive] = useState(false)
  const [torchSupported, setTorchSupported] = useState(false)
  const [facingMode, setFacingMode] = useState('environment')
  const [shutterFlash, setShutterFlash] = useState(false)
  const [topReview, setTopReview] = useState(null)
  const streamRef = useRef(null)

  const processImage = useCallback(async (base64) => {
    setRetakeError(null)
    setValidating(true)
    let validation
    try {
      validation = await validatePhoto(base64, step)
    } catch {
      setValidating(false)
      setRetakeError(t('camera.checkFailed'))
      return
    }
    setValidating(false)

    if (step === 'top' && validation.roi_review_available && !['invalid_image', 'camera_feed_blank', 'too_blurry'].includes(validation.failure_reason)) {
      setTopReview({ image: base64, box: validation.top_nail_bbox ?? null })
      return
    }

    if (!validation.ok) {
      setRetakeError(failureReasonMessage(t, validation.failure_reason))
      return
    }

    if (step === 'side') {
      setSideImage(base64)
      setStep('top')
    } else {
      onCapture({ sideImage, topImage: base64 })
    }
  }, [step, sideImage, onCapture, t])

  const confirmTop = async (topNailBbox) => {
    setValidating(true)
    setRetakeError(null)
    try {
      const validation = await validatePhoto(topReview.image, 'top', topNailBbox)
      if (validation.ok) onCapture({ sideImage, topImage: topReview.image, topNailBbox })
      else setRetakeError(failureReasonMessage(t, validation.failure_reason))
    } catch {
      setRetakeError(t('camera.checkFailed'))
    } finally {
      setValidating(false)
    }
  }

  const handleCapture = useCallback(async () => {
    const video = webcamRef.current?.video
    // make sure the camera is actually giving us a real frame, not a blank one
    if (!video || video.readyState < 2 || video.videoWidth === 0) {
      setCameraError(t('camera.captureFailed'))
      return
    }

    // Crop to the on-screen guide box (plus margin) rather than sending the
    // full frame -- both CV tracks need a tight, single-finger silhouette, not
    // a whole-hand photo. See cameraGuide.js for why the crop is asymmetric
    // (the bottom edge is deliberately left uncropped).
    const viewportRect = video.getBoundingClientRect()
    const videoRect = mapViewportRectToVideoRect(
      cropRect(step), viewportRect.width, viewportRect.height, video.videoWidth, video.videoHeight,
    )
    const sx = Math.round(videoRect.x * video.videoWidth)
    const sy = Math.round(videoRect.y * video.videoHeight)
    const sw = Math.round(videoRect.w * video.videoWidth)
    const sh = Math.round(videoRect.h * video.videoHeight)

    const canvas = document.createElement('canvas')
    canvas.width = sw
    canvas.height = sh
    const ctx = canvas.getContext('2d')
    if (!ctx || sw <= 0 || sh <= 0) {
      setCameraError(t('camera.captureFailed'))
      return
    }
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, sw, sh)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
    const base64 = dataUrl.split(',')[1]
    if (!base64) {
      setCameraError(t('camera.captureFailed'))
      return
    }

    // Shutter flash animation
    setShutterFlash(true)
    setTimeout(() => setShutterFlash(false), 150)

    await processImage(base64)
  }, [processImage, t, step])

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileChange = useCallback((e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setCameraError(null)
    const reader = new FileReader()
    reader.onload = () => {
      const base64 = String(reader.result).split(',')[1]
      processImage(base64)
    }
    reader.onerror = () => {
      setRetakeError(t('camera.fileFailed'))
    }
    reader.readAsDataURL(file)
  }, [processImage, t])

  const handleUserMedia = useCallback((stream) => {
    streamRef.current = stream
    const capabilities = stream.getVideoTracks()[0]?.getCapabilities?.() ?? {}
    setTorchSupported(!!capabilities.torch)
  }, [])

  const toggleFlash = useCallback(async () => {
    const track = streamRef.current?.getVideoTracks?.()[0]
    if (!track) return
    const next = !flashActive
    try {
      await track.applyConstraints({ advanced: [{ torch: next }] })
      setFlashActive(next)
    } catch {
      setTorchSupported(false)
    }
  }, [flashActive])

  const toggleCamera = useCallback(() => {
    setFlashActive(false)
    setTorchSupported(false)
    setFacingMode((mode) => (mode === 'environment' ? 'user' : 'environment'))
  }, [])

  if (topReview) {
    return <NailBoxSelector image={topReview.image} initialBox={topReview.box}
      busy={loading || validating} error={retakeError} onConfirm={confirmTop}
      onRetake={() => { setTopReview(null); setRetakeError(null) }} />
  }

  const isSide = step === 'side'
  const isBusy = loading || validating

  return (
    <div className="cam-fullscreen">
      {/* Live viewfinder background */}
      <div className="cam-viewfinder">
        {cameraError ? (
          <div className="cam-viewfinder-error" role="alert">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <line x1="2" y1="2" x2="22" y2="22" />
            </svg>
            <p>{cameraError}</p>
          </div>
        ) : (
          <Webcam
            ref={webcamRef}
            audio={false}
            screenshotFormat="image/jpeg"
            videoConstraints={{ facingMode }}
            className="cam-video"
            onUserMedia={handleUserMedia}
            onUserMediaError={() => setCameraError(t('camera.cameraBlocked'))}
          />
        )}
        {/* Shutter flash overlay */}
        {shutterFlash && <div className="cam-shutter-flash" />}
      </div>

      {/* Finger guide overlay */}
      {!cameraError && (
        <div className="cam-guide-overlay">
          <svg className="cam-track" viewBox="0 0 100 100" aria-hidden="true">
            <circle className="cam-track-circle" cx="50" cy="50" r="48" />
            <g className="cam-track-spin">
              <rect className="cam-track-diamond" x="19" y="19" width="62" height="62" />
              <circle cx="19" cy="19" r="1.6" /><circle cx="81" cy="19" r="1.6" />
              <circle cx="19" cy="81" r="1.6" /><circle cx="81" cy="81" r="1.6" />
            </g>
          </svg>
          <div className={`cam-guide-ring ${isSide ? 'cam-guide-ring--landscape' : 'cam-guide-ring--zoom'}`}>
            <FrameGuideSilhouette step={step} />
            <div className="cam-guide-corners">
              <span /><span /><span /><span />
            </div>
          </div>
        </div>
      )}

      {/* ─── Top bar ─── */}
      <header className="cam-top-bar">
        <button
          type="button"
          className="cam-glass-btn"
          aria-label={t('camera.close')}
          onClick={onClose}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="cam-step-center">
          <span className="cam-step-label">{t(`camera.steps.${step}.shortLabel`)}</span>
          <div className="cam-progress-dots" aria-hidden="true">
            <span className={`cam-dot ${isSide ? 'cam-dot--active' : 'cam-dot--done'}`} />
            <span className={`cam-dot ${!isSide ? 'cam-dot--active' : ''}`} />
          </div>
        </div>

        <div className="cam-step-badge" aria-label={t('camera.stepOf', { n: isSide ? 1 : 2 })}>
          <span className="cam-step-num" aria-hidden="true">{isSide ? '1' : '2'}</span>
          <span className="cam-step-of" aria-hidden="true">/2</span>
        </div>
      </header>

      {/* ─── Instruction banner ─── */}
      <div className="cam-instruction-banner" aria-live="polite">
        <p>{t(`camera.steps.${step}.instructions`)}</p>
      </div>

      {/* ─── Retake error toast ─── */}
      {retakeError && (
        <div className="cam-error-toast" role="alert">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{retakeError}</span>
          <button type="button" className="cam-toast-dismiss" aria-label={t('camera.dismiss')} onClick={() => setRetakeError(null)}>✕</button>
        </div>
      )}

      {/* ─── Bottom controls ─── */}
      <div className="cam-bottom-controls">
        {/* Status text */}
        {isBusy && (
          <div className="cam-status-pill" role="status">
            <span className="cam-status-spinner" aria-hidden="true" />
            {validating ? t('camera.checking') : t('camera.analyzing')}
          </div>
        )}

        {/* Main controls row */}
        <div className="cam-controls-row">
          {/* Flash toggle (hidden when this camera has no controllable torch) */}
          {torchSupported ? (
            <button
              type="button"
              className={`cam-glass-btn cam-side-btn ${flashActive ? 'cam-glass-btn--active' : ''}`}
              aria-label={t('camera.flash')}
              aria-pressed={flashActive}
              onClick={toggleFlash}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill={flashActive ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </button>
          ) : (
            <span className="cam-side-btn" aria-hidden="true" />
          )}

          {/* Shutter button */}
          <button
            type="button"
            className={`cam-shutter ${isBusy ? 'cam-shutter--busy' : ''}`}
            aria-label={t('camera.capture')}
            onClick={handleCapture}
            disabled={isBusy || !!cameraError}
          >
            <span className="cam-shutter-ring">
              <span className="cam-shutter-inner">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <circle cx="12" cy="13" r="3" />
                </svg>
              </span>
            </span>
          </button>

          {/* Switch camera */}
          <button
            type="button"
            className="cam-glass-btn cam-side-btn"
            aria-label={t('camera.switchCam')}
            onClick={toggleCamera}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>

        {/* Upload existing photo instead */}
        <button
          type="button"
          className="cam-upload-link"
          onClick={handleUploadClick}
          disabled={isBusy}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <path d="M21 15l-5-5L5 21" />
          </svg>
          {t('camera.upload')}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        {/* Home indicator pill */}
        <div className="cam-home-pill" />
      </div>
    </div>
  )
}
