const COPY = {
  within: {
    icon: '✓',
    label: 'Within typical range',
    message:
      'Keep an eye on changes over time, and always follow up on any health concerns with a doctor.',
  },
  outside: {
    icon: '!',
    label: 'Outside typical range',
    message: 'This is worth showing a doctor. It is not a diagnosis.',
  },
}

export default function ResultView({ result, onReset }) {
  const copy = COPY[result.verdict] ?? COPY.within

  return (
    <div className="result-card">
      <div className="result-icon">{copy.icon}</div>
      <div className="result-angle">{result.angle.toFixed(1)}°</div>
      <div className={`result-verdict ${result.verdict}`}>{copy.label}</div>
      <p className="result-message">{copy.message}</p>

      <button type="button" className="secondary-btn" onClick={onReset}>
        Scan again
      </button>

      <p className="result-disclaimer">
        Lovibond is an educational screening tool, not a medical device. It does not
        diagnose any condition. Always consult a doctor about health concerns.
      </p>
    </div>
  )
}
