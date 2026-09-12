const PATHS = {
  home: (
    <>
      <path d="M3 11l9-8 9 8" />
      <path d="M5 10v10h5v-6h4v6h5V10" />
    </>
  ),
  camera: (
    <>
      <path d="M8.3 7l1.3-2.4a1 1 0 01.9-.6h3a1 1 0 01.9.6L15.7 7" />
      <rect x="3" y="7" width="18" height="13" rx="2.5" />
      <circle cx="12" cy="13.4" r="3.3" />
    </>
  ),
  book: (
    <>
      <path d="M4 5.5c2-1.2 5-1.2 8 .5v13c-3-1.7-6-1.7-8-.5z" />
      <path d="M20 5.5c-2-1.2-5-1.2-8 .5v13c3-1.7 6-1.7 8-.5z" />
    </>
  ),
  clipboard: (
    <>
      <rect x="5" y="4.5" width="14" height="16.5" rx="2" />
      <rect x="9" y="2.5" width="6" height="3" rx="1" />
      <path d="M8.5 11.5h7M8.5 15.5h7" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="M20.3 20.3l-5.4-5.4" />
    </>
  ),
  finger: (
    <>
      <path d="M9.5 21v-9a2.5 2.5 0 015 0v9" />
      <path d="M9.5 12V6a2.5 2.5 0 015 0v6" />
      <path d="M9.5 21a2.5 2.5 0 01-2.5-2.5V15" />
    </>
  ),
  spoon: (
    <>
      <ellipse cx="12" cy="7.5" rx="4" ry="5" />
      <path d="M12 12.5V21" />
    </>
  ),
  sparkle: <path d="M12 2.5l2.1 6.8 7 2.2-7 2.2L12 21.5l-2.1-7.8-7-2.2 7-2.2z" />,
  eye: (
    <>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  pulse: <path d="M3 12h4l2 7 4-13.5 2 6.5h6" />,
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.3l2.8 2.8L16.5 9" />
    </>
  ),
  alertTriangle: (
    <>
      <path d="M12 3.5l9 15.5H3z" />
      <path d="M12 9.5v4" />
      <circle cx="12" cy="16.7" r="0.7" fill="currentColor" stroke="none" />
    </>
  ),
  helpCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.7 9.3a2.4 2.4 0 113.9 2c-.9.8-1.4 1.3-1.4 2.4" />
      <circle cx="12" cy="16.7" r="0.7" fill="currentColor" stroke="none" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="8.3" r="0.7" fill="currentColor" stroke="none" />
      <path d="M11 11.5h1.4v5.3" />
    </>
  ),
  x: <path d="M6 6l12 12M18 6L6 18" />,
  chevronRight: <path d="M9 6l6 6-6 6" />,
  history: (
    <>
      <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
      <path d="M3.5 4.5V9H8" />
      <path d="M12 8v4.3l3 1.8" />
    </>
  ),
  droplet: <path d="M12 3.5c3.8 4.6 5.7 7.6 5.7 10A5.7 5.7 0 016 13.5c0-2.4 1.9-5.4 6-10z" />,
  lines: <path d="M5 9h14M5 13h14M5 17h14" />,
  dots: (
    <>
      <circle cx="8" cy="8" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="14.5" cy="9" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="9.5" cy="14.5" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="16" cy="15" r="1.5" fill="currentColor" stroke="none" />
    </>
  ),
  logo: (
    <>
      <path d="M12 3a9 9 0 100 18z" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="9" fill="none" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </>
  ),
}

export default function Icon({ name, size = 20, className = '' }) {
  const content = PATHS[name]
  if (!content) return null

  return (
    <svg
      className={`icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {content}
    </svg>
  )
}
