// English is the master dictionary: every UI string lives here (and is the
// fallback when another locale is missing a key). Keep keys in sync with es.js.
export default {
  crop: {
    clubbing: "Nail shape (clubbing)",
    koilonychia: "Nail shape (spooning)",
    appearanceNote: "This finding describes the nail’s appearance in the top photo. No side-profile angle or depth was measured.",
  "title": "Select the nail",
  "instructions": "Move and resize the box around one nail. Include its edges and a little surrounding skin.",
  "photo": "Captured nail photo",
  "move": "Move nail box",
  "nw": "Resize top left",
  "ne": "Resize top right",
  "sw": "Resize bottom left",
  "se": "Resize bottom right",
  "confirm": "Use this nail",
  "retake": "Retake photo",
  "appearance": "Photo appearance"
},
  langName: 'English',

  app: {
    tagline: 'A precautionary nail-health screener',
    disclaimer:
      "This is an educational screening tool, not a diagnosis. It only flags whether your nail signs are typical or worth a doctor's look.",
    serverError: "Couldn't reach the analysis server. Is the backend running?",
    settingsLabel: 'Accessibility and language settings',
  },

  nav: {
    label: 'Main navigation',
    home: 'Home',
    scan: 'Scan',
    history: 'History',
    learn: 'Learn',
  },

  home: {
    title: 'Home',
    heroAlt: 'Illustration of a phone scanning a fingernail',
    heroTitle: "Spot nail changes worth a doctor's look",
    heroText:
      'Some nail signs of anemia, heart, lung, and liver conditions show up early - but develop too slowly to notice on your own. Two quick photos check for fourteen of them.',
    cta: 'Start a scan',
    whyTitle: 'Why it matters',
    whyRows: {
      anemia: {
        name: 'Anemia',
        text: 'Affects roughly 2 billion people worldwide - pale or spoon-shaped nails are among its earliest visible signs.',
      },
      organs: {
        name: 'Heart, lung & liver conditions',
        text: 'Clubbing and nail-color changes can appear months before these conditions are diagnosed.',
      },
      baseline: {
        name: 'Too slow to notice',
        text: 'These signs develop over months, so almost no one catches them in the mirror. A photo baseline makes the trend visible.',
      },
    },
    whoFor:
      'Built as a free first look for anyone who does not get regular checkups - never a replacement for one.',
    latestAssessment: 'Latest assessment',
    confidencePct: '{pct}% confidence',
    noScans: 'No scans yet',
    firstResult: 'Your first result will show up here.',
    scanId: 'Scan ID',
    howItWorks: 'How it works',
    steps: {
      side: { title: 'Side profile', text: 'Finger sideways, nail facing the camera.' },
      top: { title: 'Top down', text: 'Look straight down at the nail surface.' },
      read: { title: 'Get your read', text: 'A clear, non-diagnostic result for each sign.' },
    },
    screensFor: 'What NailIQ screens for',
    rows: {
      clubbing: { name: 'Digital clubbing', text: 'The angle where the nail meets the skin.' },
      koilonychia: { name: 'Koilonychia', text: 'Spoon-shaped curve of the nail plate.' },
      leukonychia: { name: 'Leukonychia', text: 'White spots or discoloration on the nail.' },
      melanonychia: { name: 'Melanonychia', text: 'A dark band running down the nail.' },
      pallor: { name: 'Pallor', text: 'A pale, washed-out nail bed color.' },
      cyanosis: { name: 'Cyanosis', text: 'A bluish or dusky tint to the nail bed.' },
      terrys_nails: { name: "Terry's nails", text: 'Mostly-white nail with a darker band at the tip.' },
      lindsays_nails: { name: "Lindsay's nails", text: 'Half-white, half-pink coloring split across the nail.' },
      onycholysis: { name: 'Onycholysis', text: 'The nail lifting away from the nail bed at the tip.' },
      beaus_lines: { name: "Beau's lines", text: 'Grooves running across the nail surface.' },
      muehrckes_lines: { name: "Muehrcke's lines", text: 'Pale bands running across the nail bed.' },
      splinter_hemorrhages: { name: 'Splinter hemorrhages', text: 'Tiny dark streaks beneath the nail.' },
      pitting: { name: 'Pitting', text: 'Small dents or pinpricks in the nail surface.' },
      onychogryphosis: {
        name: 'Onychogryphosis',
        text: 'A thickened, overgrown nail that curves over.',
      },
    },
    showAll: 'Show all {n}',
    showLess: 'Show less',
    dailyTip: 'Daily tip',
    tips: [
      'Good lighting and a plain background make your scan far more accurate.',
      'Healthy nails are usually smooth, with a slight even curve and no deep grooves.',
      'Nail changes develop slowly - checking now and then helps you notice a trend.',
      'Rest your finger against an edge to keep the side-profile photo steady and sharp.',
      'Remove nail polish before scanning so the nail surface is visible.',
      'One odd-looking nail is rarely a concern on its own - patterns across nails matter more.',
      'Frame just one finger, filling most of the frame, for the clearest read.',
    ],
  },

  camera: {
    steps: {
      side: {
        instructions:
          'Hold your finger sideways (profile view) inside the guide box, nail facing the camera. Use a plain background that fills the whole frame.',
        shortLabel: 'Side Profile',
      },
      top: {
        instructions:
          'Now photograph your finger from above inside the guide box, nail facing the camera. Use a plain background that fills the whole frame.',
        shortLabel: 'Top Down',
      },
    },
    close: 'Close camera',
    flash: 'Toggle flash',
    switchCam: 'Switch camera',
    capture: 'Capture photo',
    dismiss: 'Dismiss message',
    checkFailed: "Couldn't check that photo. Is the backend running?",
    captureFailed: "Couldn't capture an image. Make sure your camera is allowed and try again.",
    cameraBlocked: 'Camera access was blocked or unavailable. Check your browser permissions and reload.',
    fileFailed: "Couldn't read that file. Try a different photo.",
    checking: 'Checking photo…',
    analyzing: 'Analyzing…',
    upload: 'Upload a photo instead',
    stepOf: 'Step {n} of 2',
  },

  verdict: {
    within: {
      label: 'Within typical range',
      message:
        'Keep an eye on changes over time, and always follow up on any health concerns with a doctor.',
    },
    outside: {
      label: 'Outside typical range',
      message: 'This is worth showing a doctor. It is not a diagnosis.',
    },
    inconclusive: {
      label: "Couldn't analyze this photo",
    },
  },

  result: {
    reportTitle: 'NailIQ Nail Health Screening Report',
    summaryWithin: 'Everything looks within the typical range.',
    summaryOutsideOne: '1 sign is outside the typical range.',
    summaryOutside: '{n} signs are outside the typical range.',
    summaryInconclusive: "We couldn't analyze this scan - try retaking your photos.",
    howSure: 'How sure we are',
    noSignsRead: 'No signs could be read',
    signsUnreadOne: "1 sign couldn't be read",
    signsUnread: "{n} signs couldn't be read",
    inTheseReadings: 'in these readings',
    worthFollowingUp: 'Worth following up',
    notARiskScore: 'Not a diagnosis or risk score.',
    low: 'Low',
    some: 'Some',
    high: 'High',
    photoQuality: 'Photo quality',
    qualityGood: 'Good',
    qualityFair: 'Fair',
    qualityPoor: 'Poor',
    bothClear: 'Both photos were clear',
    sidePhoto: 'side photo',
    topPhoto: 'top-down photo',
    issueBlurry: 'blurry',
    issueGlare: 'glare',
    issuePolish: 'nail polish',
    nextSteps: 'Next steps',
    nextStepsOutside:
      "One or more signs came back outside the typical range. This isn't a diagnosis - it's worth showing a doctor, especially if you've noticed other symptoms.",
    nextStepsFallback: 'Worth mentioning to a doctor.',
    nextStepsDoctor:
      'A primary-care doctor or dermatologist is the right person to show this to. Use "Save / print report" below to bring a copy - the measured values are more useful than a description from memory.',
    nextStepsInconclusiveOne:
      "We couldn't analyze one sign from these photos. Retaking them in brighter, even light with the nail filling the frame usually fixes it.",
    nextStepsInconclusive:
      "We couldn't analyze {n} signs from these photos. Retaking them in brighter, even light with the nail filling the frame usually fixes it.",
    nextStepsWithin:
      'Everything looked within the typical range. Nothing to act on now - keep an eye on changes over time, and follow up on any health concerns with a doctor.',
    groupCloserLook: 'Worth a closer look',
    groupCouldntAnalyze: "Couldn't analyze",
    diagramOverviewAlt: 'Illustration showing where each sign from this scan was found',
    diagramOverviewNote: 'A simplified illustration of where these signs show up - not to scale, not a photo of your nail.',
    diagramClubbing: 'Clubbing',
    diagramKoilonychia: 'Koilonychia',
    withinCount: '{n} within typical range',
    closestMatch: 'Closest visual match: {label} · {pct}% confidence',
    mlClosestMatch: "AI model's closest visual match: {label}",
    savePrint: 'Save / print report',
    scanAgain: 'Scan again',
    disclaimer:
      'NailIQ is an educational screening tool, not a medical device. It does not diagnose any condition. Always consult a doctor about health concerns.',
    sources:
      'Method & honesty: the clubbing-angle threshold follows Hsu et al. (2024); the color and texture checks use uncalibrated heuristic thresholds and are screening signals, not measurements. Color readings adjust for lighting and skin tone, but real-world accuracy is unverified.',
    measuredCaption: 'The box shows the nail area the color checks measured.',
    photoAlt: 'Your top-down nail photo',
    measuredToggle: 'Measured area',
    gradcamToggle: 'AI attention',
    gradcamCaption: "Warmer colors show where the AI model's prediction came from.",
    gradcamAlt: "Heatmap showing which part of your nail the AI model's prediction was based on",
    badgeMl: 'AI model',
    badgeFused: 'Geometry + AI',
    badgeColor: 'Color check',
    badgeColorFused: 'Color + AI',
    feedbackQ: 'Does this match what you see?',
    feedbackYes: 'Yes',
    feedbackNo: 'No',
    feedbackThanks: 'Thanks - that helps us improve.',
    feedbackImpact: 'Your answers help calibrate future results.',
    toneCaveat: {
      limited:
        'This skin tone is under-represented in our test data, so this color reading is less validated for you - treat it as a weaker signal.',
      minimal:
        "We have very little validation data for darker skin tones, so this color reading may be unreliable for you. Don't read much into it.",
    },
    agreement: {
      agree: 'The shape measurement and the AI model agree on this.',
      geometry_only: "Based on the shape measurement; the AI model wasn't conclusive here.",
    },
    colorAgreement: {
      agree: 'The color check and the AI model agree on this.',
      color_only: "Based on the color check; the AI model wasn't conclusive here.",
      ml_primary: 'Based mainly on the AI model here.',
      ml_only: 'Based on the AI model alone - there is no simpler color check for this sign.',
    },
    mlLabels: {
      clubbing: 'clubbing-type appearance',
      koilonychia: 'koilonychia-type (spoon) appearance',
      healthy: 'a typical, healthy-looking nail',
      cyanosis: 'a bluish (cyanosis-type) appearance',
      terrys_nails: "a Terry's-nail-type appearance",
      beaus_lines: "a Beau's-line-type groove",
      muehrckes_lines: "a Muehrcke's-line-type banding",
      pitting: 'a pitting-type surface',
      onychogryphosis: 'a thickened, overgrown (onychogryphosis-type) nail',
      pallor: 'a pale (pallor-type) appearance',
    },
  },

  history: {
    title: 'History',
    loading: 'Loading your past scans…',
    error: "Couldn't load your scan history. Is the backend running?",
    empty: 'No scans yet. Your past results will show up here so you can track changes over time.',
    rescanNote:
      'Nails grow about 3 mm per month, so these signs change slowly. A monthly rescan makes a trend visible long before it is obvious in the mirror.',
    placeholderNote: 'Showing example scans. Take your first scan to replace these with real results.',
    example: 'Example',
    changed: 'Changed',
    changedSinceLast: 'Changed since last scan',
    withinRange: 'Within range',
    outsideRange: 'Outside range',
    inconclusive: 'Inconclusive',
    measuredAngle: 'Measured angle',
    measuredValue: 'Measured value',
    clubbingThreshold: '> 180° threshold',
    confidenceScore: 'Confidence score',
    fusedNote: 'Result fused from multiple analysis models for higher accuracy.',
    colorFusedNote: 'Result fused from a color check and an AI model for higher accuracy.',
    trendTitle: 'Clubbing angle over time',
    trendAngle: 'Angle',
    trendNote:
      'This tracks the measured angle only, not a diagnosis. Share this trend with a doctor if you have concerns.',
  },

  info: {
    intro:
      'NailIQ screens every photo for all of these signs. Tap any one to learn what it looks like, why it happens, and what your result means.',
    close: 'Close',
  },

  failure: {
    invalid_image: "That photo couldn't be processed. Please try again.",
    camera_feed_blank:
      "We didn't get an actual image from your camera. Check that camera access is allowed, then reload and try again.",
    too_blurry:
      'That photo looks blurry. Hold your hand and camera steady, let it focus, and retake the shot.',
    no_contour_found:
      "We couldn't find your finger in that photo. Make sure it fills the frame against a plain background.",
    contour_too_small: 'Your finger looks too small in the frame. Move the camera closer and try again.',
    contour_degenerate: "That photo couldn't be processed. Please try again.",
    background_not_filling_frame:
      "Something behind your finger is being read as part of it. Use a plain surface that fills the whole frame, then retake.",
    fingertip_cropped:
      'Your fingertip is cut off at the edge of the frame. Move it fully into view and retake.',
    fingertip_not_clear:
      "We couldn't get a clear view of your fingertip. Try better lighting and hold the camera steady.",
    cuticle_not_detected:
      "We couldn't find your nail and cuticle clearly. Make sure your whole nail is visible, nail facing the camera.",
    points_too_close:
      "We couldn't get a clear read on your nail shape. Try repositioning your finger and retaking the photo.",
    points_collinear:
      "We couldn't get a clear read on your nail shape. Try repositioning your finger and retaking the photo.",
    measurement_unstable:
      "We couldn't measure your nail's side profile consistently - small changes to the photo gave different results, so we're not calling it. Retake the side photo steady, in even light, against a plain background.",
    angle_implausible:
      "The nail angle we measured isn't physically plausible, so the outline was probably misread. Retake the side photo with your finger fully side-on to the camera.",
    measurement_borderline:
      "Your nail angle measured right at the edge of the typical range, too close to call reliably. Retake the side photo steady and side-on; consider showing a doctor if you're concerned.",
    not_validated:
      "We haven't yet shown this check is reliable enough on held-out photos, so we're not giving a result for it rather than risk a wrong one. If you're concerned about this sign, show a doctor.",
    heuristic_uncorroborated:
      "Only the simpler color check flagged this, and the AI model saw no sign of it, so we're not calling it either way. Retake the top-down photo in even light; consider showing a doctor if you're concerned.",
    low_confidence:
      "The AI model wasn't confident enough about this photo to give a read. Try a clearer, well-lit shot of a single nail.",
    nail_region_unclear:
      "We couldn't get a clear read on your nail plate from the top-down photo. Fill the frame with your nail in even lighting and retake it.",
    nail_polish_detected:
      "It looks like there's nail polish on. Color and surface signs can't be read through polish - remove it and retake the top-down photo.",
    too_much_glare:
      "There's too much glare on the nail to read its color. Tilt away from direct light or move to softer lighting, then retake the photo.",
    tracks_disagree:
      "Our two checks didn't agree on this one, so we're not calling it either way. Retake both photos in good lighting, and consider showing a doctor if you're concerned.",
    insufficient_data_for_confident_call:
      "We don't have enough validated data on this sign to call it confidently, and our two checks didn't agree. Retake in good lighting, and consider showing a doctor if you're concerned.",
    requires_ai_model: 'This sign can only be checked by the AI model, which isn\'t available right now, so we\'re not giving a result for it.',
    no_confident_ai_call: 'The AI model wasn\'t confident enough about this sign in your photo to call it either way. Retake the top-down photo in even light with the whole nail in view; consider showing a doctor if you\'re concerned.',
    default:
      "We couldn't detect a nail in that photo. Try a plainer background, better lighting, and your whole finger in frame.",
  },

  status: {
    outsideCount: '{n} outside typical range',
    allWithin: 'All within typical range',
    cantAnalyze: "Couldn't analyze this scan",
  },

  time: {
    justNow: 'Just now',
    minutesAgo: '{n}m ago',
    hoursAgo: '{n}h ago',
    yesterday: 'Yesterday',
    daysAgo: '{n}d ago',
  },

  diagram: {
    typical: 'Typical',
    typicalSub: 'even, smooth',
    sign: 'Sign',
    alt: 'Top view of a typical nail versus one showing {sub}',
    fallbackSub: 'a sign',
    imgAlts: {
      clubbing:
        'Side-by-side comparison of a clubbed finger (enlarged bulbous tip, downward-curving nail, wider nail bed) versus a normal finger (tapered tip, flatter nail, narrower nail bed)',
      koilonychia:
        'Side-by-side comparison of normal nails (flat or gently domed, convex cross-section) versus koilonychia (spoon-shaped nails that dip concave in the middle)',
      leukonychia:
        'Side-by-side comparison of normal nails versus leukonychia (scattered punctate white spots across the nail plate)',
      melanonychia:
        'Side-by-side comparison of normal nails versus melanonychia (a single dark brown-black longitudinal band running down the nail plate)',
      pallor:
        'Side-by-side comparison of a normal pink nail bed versus pallor (a pale, washed-out nail bed)',
      cyanosis:
        'Side-by-side comparison of a normal pink nail bed versus cyanosis (a bluish, dusky nail bed)',
      terrys_nails:
        "Side-by-side comparison of normal nails versus Terry's nails (a mostly white, opaque nail plate with a narrow dark band at the tip)",
      lindsays_nails:
        "Side-by-side comparison of normal nails versus Lindsay's (half-and-half) nails (a dull-white proximal half and a darker pink-brown distal half with a sharp dividing line)",
      onycholysis:
        'Side-by-side comparison of normal nails versus onycholysis (the nail plate separating and lifting from the nail bed at the distal free edge, leaving a white or yellow-white detached area)',
      beaus_lines:
        "Side-by-side comparison of normal nails versus Beau's lines (a transverse groove or depression running across the nail plate)",
      muehrckes_lines:
        "Side-by-side comparison of normal nails versus Muehrcke's lines (a pair of transverse white bands running across the nail plate)",
      splinter_hemorrhages:
        'Comparison of normal nails versus typical splinter hemorrhages (small, thin, reddish-brown vertical lines under the nail)',
      pitting:
        'Side-by-side comparison of normal nails (smooth surface) versus nail pitting (numerous small, distinct, irregular depressions scattered across the nail plate)',
    },
    subs: {
      leukonychia: 'white spots',
      melanonychia: 'dark band',
      pallor: 'pale',
      cyanosis: 'bluish',
      terrys_nails: 'white, dark tip',
      lindsays_nails: 'half & half',
      onycholysis: 'tip lifted',
      beaus_lines: 'groove across',
      muehrckes_lines: 'white bands',
      splinter_hemorrhages: 'tiny streaks',
      pitting: 'small pits',
      onychogryphosis: 'thick, curved',
    },
  },

  settings: {
    title: 'Settings',
    open: 'Open settings',
    close: 'Close settings',
    language: 'Language',
    display: 'Display & motion',
    darkMode: 'Dark mode',
    darkModeDesc: 'Use a dark color theme. Follows your device setting unless changed here.',
    highContrast: 'High contrast',
    highContrastDesc: 'Stronger colors and outlines for easier reading.',
    largeText: 'Larger text',
    largeTextDesc: 'Increase text size across the app.',
    reduceMotion: 'Reduce motion',
    reduceMotionDesc: 'Turn off animations and transitions.',
    note: 'These settings are saved on this device.',
    privacyLink: 'Privacy policy',
  },

  privacy: {
    title: 'Privacy policy',
    close: 'Close privacy policy',
    photosTitle: 'Your photos',
    photosBody:
      'Your two photos are analyzed in memory and then discarded. No photo is ever saved to disk or to the database - only the findings (labels, verdicts, confidence) are stored.',
    storedTitle: 'What is stored',
    storedBody:
      'Scan findings are saved locally so History and the angle-trend chart can show past scans. If you answer "does this match what you see?", that response is stored the same way to help calibrate the app later - avoid putting anything identifying in the note field. Display and language settings are stored only on this device.',
    notCollectedTitle: 'What is not collected',
    notCollectedBody: 'No accounts, names, emails, or device identifiers are requested or stored anywhere in this app.',
    limitationTitle: 'Known limitation',
    limitationBody:
      'This is a single-deployment prototype: History shows every scan stored on this backend, with no per-user separation. Treat it accordingly if this backend is ever shared beyond one person.',
    disclaimer:
      'Nothing in this app is a diagnosis. Every finding is only ever "within typical range," "outside typical range," or "couldn\'t analyze this photo." Talk to a clinician about any concerning nail change.',
  },

  // Backend findings arrive with English display_name; the UI renames them by
  // label so translations work without touching the API contract.
  findingNames: {
    clubbing: 'Nail angle (clubbing)',
    koilonychia: 'Nail curvature (koilonychia)',
    leukonychia: 'Nail color (leukonychia)',
    melanonychia: 'Nail pigmentation (melanonychia)',
    pallor: 'Nail color (pallor)',
    cyanosis: 'Nail color (cyanosis)',
    terrys_nails: "Nail color (Terry's nails)",
    lindsays_nails: 'Nail color (half-and-half nails)',
    onycholysis: 'Nail separation (onycholysis)',
    beaus_lines: "Nail surface (Beau's lines)",
    muehrckes_lines: "Nail markings (Muehrcke's lines)",
    splinter_hemorrhages: 'Nail markings (splinter hemorrhages)',
    pitting: 'Nail surface (pitting)',
    onychogryphosis: 'Nail thickening (onychogryphosis)',
  },

  pointTitles: {
    looks: 'What it looks like',
    why: 'Why it happens',
    how: 'How NailIQ checks it',
    action: 'What to do with your result',
  },

  conditions: {
    clubbing: {
      name: 'Digital clubbing',
      summary: 'A change in the angle where the nail meets the skin.',
      lead:
        'Look at your finger from the side. Most fingers have a small notch where the nail meets the skin. Clubbing slowly smooths that notch away until the fingertip looks rounded and the nail curves over it.',
      points: {
        looks:
          "Normally there's a small dip where your nail meets the skin of your finger, like a tiny valley. With clubbing, that dip flattens out or disappears, the fingertip looks rounder and puffier, and over time the nail can start to curve down over the tip instead of lying flat.",
        why:
          "Doctors aren't fully sure why it happens, but it shows up most often alongside long-term lung problems, certain heart conditions, or some digestive diseases. It builds up slowly over months or years, so it's not something that appears overnight.",
        how:
          "We measure the angle where your nail meets your skin from the side-profile photo. A typical angle stays under about 180°. Clubbing pushes that angle past it, so it's really just careful geometry, not a guess.",
        action:
          'An "outside typical range" result does not mean you have a specific disease - it just means it is worth showing a doctor, especially if you have also noticed things like shortness of breath, a lingering cough, or unusual tiredness.',
      },
    },
    koilonychia: {
      name: 'Koilonychia (spoon nails)',
      summary: 'Nails that curve upward like a spoon instead of lying flat.',
      lead:
        'Look straight down at your nail. A typical nail is flat or gently domed. A spoon nail dips inward in the middle - sometimes deep enough that a drop of water would sit in it instead of rolling off.',
      points: {
        looks:
          'Instead of staying flat or curving gently outward, the middle of the nail dips inward, like a tiny spoon. In more noticeable cases, the nail is thin and curved enough that a drop of water would actually sit in the dip instead of rolling off.',
        why:
          'The most common cause is low iron in the blood, also called iron-deficiency anemia. It can also show up with thyroid changes, some skin conditions, or a lot of exposure to solvents and harsh detergents. In babies and young kids, slightly spoon-shaped nails are often totally normal and grow out on their own.',
        how:
          'We measure how far the middle of your nail curves away from a straight line drawn between your cuticle and fingertip, then scale that by the length of your nail so it works fairly across different finger sizes.',
        action:
          'An "outside typical range" result is worth mentioning to a doctor, especially if you also feel unusually tired, look pale, or have brittle nails - those can point toward anemia, which is easy to test for with a simple blood test and easy to treat.',
      },
    },
    leukonychia: {
      name: 'Leukonychia (white marks)',
      summary: 'White spots or patches on the nail surface.',
      lead:
        'White spots, lines, or patches on the nail are called leukonychia. Sometimes just a few spots appear after a bump or minor injury. Sometimes larger areas of the nail look whitish instead of the usual pink-and-white color.',
      points: {
        looks:
          'White marks can appear as small round spots, thin horizontal lines, larger cloudy patches, or in some cases most of the nail bed looks white or opaque instead of the typical pink color under the nail plate.',
        why:
          'Small white spots usually come from minor trauma or bumps to the nail. Widespread whitening of the nail bed can relate to liver disease, kidney disease, heart problems, diabetes, or nutritional issues - but it can also be totally harmless. Only a doctor can tell the difference.',
        how:
          'We estimate the nail plate from a top-down photo and look for white or opaque areas in the nail, adjusting for your skin tone. These are screening signals, not precise measurements - lighting and phone camera differences affect the result.',
        action:
          'If you see extensive white coloring on your nails, especially if it shows up across multiple fingers, it is worth mentioning to a doctor - they can examine you properly and run any tests if needed. Small white spots from minor bumps typically fade on their own.',
      },
    },
    melanonychia: {
      name: 'Melanonychia (dark band)',
      summary: 'A brown or black band running lengthwise on the nail.',
      lead:
        "A dark longitudinal band - a stripe running from the cuticle to the tip - is called melanonychia. It is very common, especially in people with darker skin tones, and is often completely benign. But a new band or one that is changing warrants a doctor's look.",
      points: {
        looks:
          'A brown, black, or dark-gray stripe runs lengthwise down the nail from the cuticle to the tip, sometimes involving the full width of the nail or just part of it. The band can be narrow or quite wide.',
        why:
          "The most common cause is pigment in the nail-forming cells (melanocytes), which is especially common in people with darker skin and is almost always benign. Bands can also come from moles, birthmarks, medications (like some chemotherapy drugs), or in rare cases, melanoma. A new or changing band deserves a doctor's attention.",
        how:
          'We estimate the nail plate and look for dark brown or black pigmentation along the length of the nail. NailIQ adjusts its sensitivity based on your skin tone to account for normal variation. These checks are screening signals, not diagnostic.',
        action:
          "If a dark band is longstanding and unchanged, it is very likely harmless. If it is new, widening, or changing color or shape, or if you are unsure how long you've had it, show it to a doctor - they can examine it and decide if further testing is needed.",
      },
    },
    pallor: {
      name: 'Pallor (pale nails)',
      summary: 'An unusually pale or white nail bed.',
      lead:
        'Most nails have a pink nail bed with a white tip. When the nail bed is unusually pale or white instead, it can sometimes relate to low blood iron, anemia, liver disease, or kidney issues - but it can also be normal variation.',
      points: {
        looks:
          'The nail bed (the part under the transparent nail plate) looks pale, whitish, or almost colorless instead of the typical pink color. The very tip of the nail may still be white, but the middle and base look less pink than usual.',
        why:
          "Pale nails can relate to low red blood cell count (anemia), low iron, liver disease, kidney disease, or reduced blood flow to the fingers. They can also just be a normal variation in skin tone. A doctor needs to examine you and possibly run blood tests to figure out what's causing it.",
        how:
          'We analyze the nail bed color from a top-down photo and look for paleness or whitening, adjusting for your skin tone. This is a screening signal only - it is not a measure of blood counts or oxygen levels.',
        action:
          'Widespread pale nails, especially across multiple fingers, are worth mentioning to a doctor during an exam. If you also feel tired, dizzy, or short of breath, mention those symptoms too - they may help your doctor decide if blood work is needed.',
      },
    },
    cyanosis: {
      name: 'Cyanosis (bluish nails)',
      summary: 'A bluish or purple tint to the nails.',
      lead:
        'When nails have a bluish or purple tint instead of the usual pink and white, it is called cyanosis. This can relate to low oxygen in the blood, cold exposure, or heart/lung problems - but it can also be a camera artifact or lighting effect.',
      points: {
        looks:
          'The nail bed and nail plate have a bluish, purplish, or grayish tint instead of the typical pink color. The discoloration may involve the whole nail or be most noticeable in the nail bed.',
        why:
          'True cyanosis (a bluish tint from low blood oxygen) can happen with lung disease, heart disease, or severe cold exposure. Nails can also look blue or purple from bruising, old age, cold fingers, or certain medications. Nail fungus can sometimes cause a bluish tint too.',
        how:
          'We analyze the color of the nail bed and plate from a top-down photo and look for bluish or purple hues. Be aware that lighting, phone camera white-balance, and nail polish can affect this - these checks are screening signals, not an oxygen measurement.',
        action:
          'If your nails look genuinely bluish and you also notice shortness of breath, chest pain, or your lips or tongue look blue, seek medical attention right away. If nails just look slightly blue on photos but you feel fine, it may be a camera artifact - a doctor can examine your nails in person to clarify.',
      },
    },
    terrys_nails: {
      name: "Terry's nails",
      summary: 'Most of the nail white or opaque with a narrow dark band at the tip.',
      lead:
        "In Terry's nails, the nail bed looks mostly white or opaque, leaving only a narrow reddish-brown or dark band at the very tip. This pattern is often tied to liver disease, heart failure, kidney disease, or diabetes.",
      points: {
        looks:
          'Most of the nail (roughly two-thirds to three-quarters) looks white, opaque, or pale. Just the distal tip shows a distinct darker reddish-brown band, usually 1-3mm wide. Sometimes a thin pale line separates the white area from the dark band.',
        why:
          "Terry's nails are most often seen with liver disease, kidney disease, heart failure, or diabetes. They can also show up after chemotherapy or with aging. The exact cause is not fully understood, but the nail bed changes in a way that makes it appear whiter. It is considered a clinical sign worth investigating.",
        how:
          "We estimate the nail plate and look for a sharp transition between a mostly white nail bed and a darker distal band. This is a screening signal - proper diagnosis requires a doctor's examination.",
        action:
          "If your nails match this pattern, especially across multiple fingers, it is worth showing to a doctor. They can check your overall health and may order tests (blood work, liver function, kidney function, heart exam) to understand what's going on.",
      },
    },
    lindsays_nails: {
      name: "Half-and-half nails (Lindsay's nails)",
      summary: 'Proximal half white, distal half reddish-brown.',
      lead:
        "In Lindsay's nails, there is a sharp line across the middle of the nail: the half closer to the cuticle is white or pale, and the half toward the tip is reddish-brown or pink. This pattern is often associated with kidney disease.",
      points: {
        looks:
          'A horizontal line divides the nail roughly in half: the proximal half (near the cuticle) is white, opaque, or pale, and the distal half (toward the tip) is reddish, pink, or brown. The demarcation line is usually sharp and distinct.',
        why:
          "Lindsay's nails are classically associated with kidney disease and kidney failure, especially in patients on dialysis. They can also occur with other serious illnesses like liver disease or leukemia. The exact cause is unknown, but the pattern is considered a clinical sign worth investigating.",
        how:
          'We estimate the nail boundaries and look for a clear horizontal band separating a white proximal half from a darker distal half. This is a screening signal based on color and positioning.',
        action:
          "If your nails show this pattern, especially across multiple fingers, bring it to a doctor's attention. If you have any history of kidney problems, diabetes, or liver disease, mention that too - your doctor can order appropriate tests and follow-up.",
      },
    },
    onycholysis: {
      name: 'Onycholysis (nail lifting)',
      summary: 'The nail separating from the bed, looking opaque at the free edge.',
      lead:
        'Onycholysis is when the nail begins to separate from the underlying nail bed, starting at the free edge and working backward toward the cuticle. The separated part looks opaque or white instead of the clear color it would have if still attached.',
      points: {
        looks:
          'The nail lifts away from the finger starting at the tip and potentially extending back toward the cuticle. The lifted area looks opaque, whitish, or chalky instead of clear. You may be able to see air or debris under the nail in the lifted area.',
        why:
          'Onycholysis can be caused by nail trauma, thyroid disease (especially hyperthyroidism), psoriasis, fungal infection, contact dermatitis, or reactions to medications or nail products. Sometimes the cause is never found. It usually grows out as the nail replaces itself, but treatment depends on the underlying cause.',
        how:
          'We look for areas where the nail appears to separate or lift from the finger, showing as opaque or white zones especially at or near the free edge. This is a visual screening check only.',
        action:
          'If you notice nail lifting, keep the area dry and clean to prevent infection, and avoid aggressive manicuring or exposure to harsh chemicals. Show it to a doctor if it spreads quickly, gets painful, or if you develop signs of infection. Your doctor can test for thyroid disease, psoriasis, or fungus if needed.',
      },
    },
    beaus_lines: {
      name: "Beau's lines",
      summary: 'Horizontal grooves or indentations across the nail.',
      lead:
        "Beau's lines are grooves or indentations that run across the width of the nail, from side to side. They mark a temporary pause or slowdown in nail growth, usually caused by illness, high fever, surgery, or severe stress.",
      points: {
        looks:
          'One or more horizontal grooves or ridges run across the entire width of the nail from one side to the other. The grooves can be shallow or quite deep, and may be more visible on some fingers than others.',
        why:
          "Beau's lines form when the nail-growing cells pause or slow down, which happens after significant physical or emotional stress - a high fever, serious illness, surgery, severe infection, or major injury. They appear roughly in the area of the nail that was growing at the time of the stress. As the nail grows out, the line slowly moves toward the tip and eventually disappears.",
        how:
          'We analyze the nail surface for horizontal indentations or grooves that run across the width. This is a visual screening check based on surface texture.',
        action:
          "If you notice Beau's lines, try to recall if you had a significant illness, high fever, surgery, or major stress about 6-12 weeks earlier - the timeline usually matches. Beau's lines themselves are harmless and fade as the nail grows out. If you have recurring lines or other concerning nail changes, mention them to a doctor.",
      },
    },
    muehrckes_lines: {
      name: "Muehrcke's lines",
      summary: 'Paired white bands across the nail that do not move as the nail grows.',
      lead:
        "Muehrcke's lines are pairs of white bands that run horizontally across the nail. Unlike Beau's lines, they stay in the same position relative to the cuticle as the nail grows - they don't move toward the tip. They often relate to low blood protein or kidney disease.",
      points: {
        looks:
          "Two white bands run horizontally across the nail, usually in the middle or proximal region. The bands are separated by a thin line of normal nail color. Unlike Beau's lines (grooves), Muehrcke's lines are flat (no indentation) - they are purely a color change.",
        why:
          "Muehrcke's lines are classically associated with low blood protein (hypoalbuminemia), which can happen with kidney disease, liver disease, malnutrition, or other serious illnesses. They can also show up temporarily during pregnancy or with certain cancers. The lines reflect a change in the nail bed itself and stay in place as the nail grows (unlike Beau's lines, which move toward the tip).",
        how:
          'We look for paired horizontal white bands on the nail that are flat (not grooved) and stay in roughly the same position across the nail width. This is a visual screening check.',
        action:
          'If you notice this pattern, especially on multiple nails, bring it to a doctor. It often points to a kidney or liver issue that deserves investigation. Your doctor can order blood tests to check protein levels, kidney function, and liver function.',
      },
    },
    splinter_hemorrhages: {
      name: 'Splinter hemorrhages',
      summary: 'Tiny dark streaks under the nail running lengthwise.',
      lead:
        'Splinter hemorrhages are small dark red, brown, or black streaks that run lengthwise under the nail. They look like tiny splinters of wood. Most are caused by minor trauma, but they can occasionally relate to infections or other conditions.',
      points: {
        looks:
          'One or more thin, dark (red, brown, or black) streaks run lengthwise under the nail, from the nail bed toward the tip. They look like tiny splinters, usually a few millimeters long. They are most noticeable in the middle or distal portions of the nail.',
        why:
          'Most splinter hemorrhages come from minor bumps or trauma to the finger that damage small blood vessels under the nail. They heal on their own as the nail grows out. Occasionally, they can be a sign of a blood infection (endocarditis), especially if they appear on multiple nails without any obvious injury, or if they appear alongside other symptoms like fever, chills, or a new heart murmur.',
        how:
          'We look for dark longitudinal streaks under the nail that could indicate small hemorrhages. This is a visual screening check - some dark lines could be artifacts from dirt or the phone camera.',
        action:
          'If you see a splinter hemorrhage and remember hitting your finger, it will likely fade on its own. If multiple nails develop splinter hemorrhages without any injury, or if you also have fever or feel ill, mention it to a doctor - they can evaluate whether further testing is needed.',
      },
    },
    pitting: {
      name: 'Nail pitting',
      summary: 'Small dents or pinpricks in the nail surface.',
      lead:
        'Nail pitting is the appearance of small dents, pits, or pinpricks scattered across the nail surface. Pitting is frequently seen with psoriasis, but can also show up with alopecia, connective tissue disease, or sometimes on its own.',
      points: {
        looks:
          'The nail surface has multiple small round or irregular indentations, like tiny pits or dents scattered across the nail. The pits can be shallow or deeper, and may involve just the surface or extend partially into the nail. They give the nail a rougher appearance.',
        why:
          'Pitting is most commonly linked to psoriasis (a skin condition) and alopecia areata (patchy hair loss). It can also occur with connective tissue diseases, fungal infections, or sometimes on its own without any other cause. Psoriasis-related pitting often involves multiple nails.',
        how:
          'We analyze the nail surface for small indentations and pitting patterns. This is a visual screening check based on surface texture, though camera resolution and lighting can affect how visible fine pits are.',
        action:
          'If you notice pitting on multiple nails, it is worth mentioning to a doctor, especially if you also have skin symptoms like patches or itching, or hair loss. Your doctor can examine you and decide if testing or further evaluation is needed.',
      },
    },
    onychogryphosis: {
      name: 'Onychogryphosis (ram\'s horn nail)',
      summary: 'A thickened, overgrown nail that curves over.',
      lead: 'Onychogryphosis is a nail that has become very thick and overgrown, often curving over like a horn. It most often affects the big toenail, but it can show up on fingernails too. It is usually caused by long-term pressure, injury, or aging, and is sometimes linked to poor circulation.',
      points: {
        looks: 'The nail is much thicker than normal, often yellow or brown, and may have ridges across it. As it grows it can curve sideways or downward over the tip of the finger or toe, sometimes like a ram\'s horn.',
        why: 'It most often comes from repeated pressure or injury to the nail (tight shoes are a common cause for toenails), getting older, or long-term lack of nail trimming. It can also be linked to poor circulation, diabetes, psoriasis, or fungal infection. Unlike most signs NailIQ checks, it is usually a local nail problem rather than a sign of a whole-body condition.',
        how: 'This check comes from the AI model alone: it learned what thickened, overgrown nails look like from labeled clinical photos. There is no separate color measurement for it, so if the model isn\'t confident, we say we couldn\'t analyze it rather than guess.',
        action: 'A thick, overgrown nail is worth showing to a doctor or podiatrist, especially if it hurts, is hard to trim, or you have diabetes or poor circulation. They can trim it safely and check for anything underneath it.',
      },
    },
  },
}
