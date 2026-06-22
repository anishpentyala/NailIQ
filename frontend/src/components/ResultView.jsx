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
  inconclusive: {
    icon: '?',
    label: "Couldn't analyze this photo",
    message:
      'Try retaking with a plainer background, better lighting, and your whole finger in frame.',
  },
}

function FindingCard({ finding }) {
  const copy = COPY[finding.verdict] ?? COPY.inconclusive

  return (
    <div className="finding-card">
      <div className="result-icon">{copy.icon}</div>
      <div className="finding-name">{finding.display_name}</div>
      {finding.value != null && (
        <div className="result-angle">
          {finding.value.toFixed(1)}
          {finding.unit === 'deg' ? '°' : ''}
        </div>
      )}
      <div className={`result-verdict ${finding.verdict}`}>{copy.label}</div>
      <p className="result-message">{copy.message}</p>
    </div>
  )
}

export default function ResultView({ result, onReset }) {
  const findings = result.findings ?? []

  return (
    <div className="result-card">
      <div className="findings-list">
        {findings.map((finding) => (
          <FindingCard key={finding.label} finding={finding} />
        ))}
      </div>

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
