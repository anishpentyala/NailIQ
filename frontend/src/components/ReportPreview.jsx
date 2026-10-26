import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import Icon from './Icon'
import { useI18n } from '../i18n'
import { savePdfFile } from '../reportShare'

// The report PDF, shown inside the app (the iPhone Home Screen app can't open or download it directly).
export default function ReportPreview({ report, onClose }) {
  const { t } = useI18n()

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return createPortal(
    <div className="sheet-overlay report-preview-overlay" onClick={onClose}>
      <div
        className="sheet report-preview"
        role="dialog"
        aria-modal="true"
        aria-label={t('result.reportTitle')}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-handle" aria-hidden="true" />
        <header className="sheet-header">
          <span className="sheet-header-icon">
            <Icon name="clipboard" size={22} />
          </span>
          <div className="sheet-header-text">
            <h2 className="sheet-title">{t('result.reportTitle')}</h2>
            <p className="sheet-subtitle">{report.file.name}</p>
          </div>
          <button type="button" className="sheet-close" onClick={onClose} aria-label={t('info.close')}>
            <Icon name="x" size={22} />
          </button>
        </header>
        <div className="sheet-body report-preview-pages">
          {report.images.map((src, i) => (
            <img key={i} className="report-preview-page" src={src} alt={`${t('result.reportTitle')} ${i + 1}`} />
          ))}
        </div>
        <div className="report-preview-actions">
          <button type="button" className="primary-btn" onClick={() => savePdfFile(report.file)}>
            {t('result.savePdf')}
          </button>
          <p className="report-preview-hint">{t('result.savePdfHint')}</p>
        </div>
      </div>
    </div>,
    document.getElementById('root'),
  )
}
