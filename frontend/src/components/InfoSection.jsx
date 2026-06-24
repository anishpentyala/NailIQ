import { useState, useEffect } from 'react'
import Icon from './Icon'
import NailDiagram from './NailDiagram'

const CONDITIONS = [
  {
    key: 'clubbing',
    icon: 'finger',
    name: 'Digital clubbing',
    summary: 'A change in the angle where the nail meets the skin.',
    lead:
      'Look at your finger from the side. Most fingers have a small notch where the nail ' +
      'meets the skin. Clubbing slowly smooths that notch away until the fingertip looks ' +
      'rounded and the nail curves over it.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          "Normally there's a small dip where your nail meets the skin of your finger, like a " +
          'tiny valley. With clubbing, that dip flattens out or disappears, the fingertip looks ' +
          'rounder and puffier, and over time the nail can start to curve down over the tip ' +
          'instead of lying flat.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          "Doctors aren't fully sure why it happens, but it shows up most often alongside " +
          'long-term lung problems, certain heart conditions, or some digestive diseases. It ' +
          "builds up slowly over months or years, so it's not something that appears overnight.",
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We measure the angle where your nail meets your skin from the side-profile photo. ' +
          "A typical angle stays under about 180°. Clubbing pushes that angle past it, so it's " +
          'really just careful geometry, not a guess.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'An "outside typical range" result does not mean you have a specific disease — it ' +
          'just means it is worth showing a doctor, especially if you have also noticed things ' +
          'like shortness of breath, a lingering cough, or unusual tiredness.',
      },
    ],
  },
  {
    key: 'koilonychia',
    icon: 'spoon',
    name: 'Koilonychia (spoon nails)',
    summary: 'Nails that curve upward like a spoon instead of lying flat.',
    lead:
      'Look straight down at your nail. A typical nail is flat or gently domed. A spoon nail ' +
      'dips inward in the middle — sometimes deep enough that a drop of water would sit in it ' +
      'instead of rolling off.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'Instead of staying flat or curving gently outward, the middle of the nail dips ' +
          'inward, like a tiny spoon. In more noticeable cases, the nail is thin and curved ' +
          'enough that a drop of water would actually sit in the dip instead of rolling off.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'The most common cause is low iron in the blood, also called iron-deficiency anemia. ' +
          'It can also show up with thyroid changes, some skin conditions, or a lot of exposure ' +
          'to solvents and harsh detergents. In babies and young kids, slightly spoon-shaped ' +
          'nails are often totally normal and grow out on their own.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We measure how far the middle of your nail curves away from a straight line drawn ' +
          'between your cuticle and fingertip, then scale that by the length of your nail so it ' +
          'works fairly across different finger sizes.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'An "outside typical range" result is worth mentioning to a doctor, especially if you ' +
          'also feel unusually tired, look pale, or have brittle nails — those can point toward ' +
          'anemia, which is easy to test for with a simple blood test and easy to treat.',
      },
    ],
  },
  {
    key: 'leukonychia',
    icon: 'sparkle',
    name: 'Leukonychia (white marks)',
    summary: 'White spots or patches on the nail surface.',
    lead:
      'White spots, lines, or patches on the nail are called leukonychia. Sometimes just a few ' +
      'spots appear after a bump or minor injury. Sometimes larger areas of the nail look whitish ' +
      'instead of the usual pink-and-white color.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'White marks can appear as small round spots, thin horizontal lines, larger cloudy ' +
          'patches, or in some cases most of the nail bed looks white or opaque instead of the ' +
          'typical pink color under the nail plate.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Small white spots usually come from minor trauma or bumps to the nail. Widespread ' +
          'whitening of the nail bed can relate to liver disease, kidney disease, heart problems, ' +
          'diabetes, or nutritional issues — but it can also be totally harmless. Only a doctor ' +
          'can tell the difference.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We estimate the nail plate from a top-down photo and look for white or opaque areas ' +
          'in the nail, adjusting for your skin tone. These are screening signals, not precise ' +
          'measurements — lighting and phone camera differences affect the result.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If you see extensive white coloring on your nails, especially if it shows up across ' +
          'multiple fingers, it is worth mentioning to a doctor — they can examine you properly ' +
          'and run any tests if needed. Small white spots from minor bumps typically fade on their own.',
      },
    ],
  },
  {
    key: 'melanonychia',
    icon: 'search',
    name: 'Melanonychia (dark band)',
    summary: 'A brown or black band running lengthwise on the nail.',
    lead:
      'A dark longitudinal band — a stripe running from the cuticle to the tip — is called ' +
      'melanonychia. It is very common, especially in people with darker skin tones, and is often ' +
      'completely benign. But a new band or one that is changing warrants a doctor\'s look.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'A brown, black, or dark-gray stripe runs lengthwise down the nail from the cuticle to ' +
          'the tip, sometimes involving the full width of the nail or just part of it. The band can ' +
          'be narrow or quite wide.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'The most common cause is pigment in the nail-forming cells (melanocytes), which is ' +
          'especially common in people with darker skin and is almost always benign. Bands can also ' +
          'come from moles, birthmarks, medications (like some chemotherapy drugs), or in rare cases, ' +
          'melanoma. A new or changing band deserves a doctor\'s attention.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We estimate the nail plate and look for dark brown or black pigmentation along the length ' +
          'of the nail. NailIQ adjusts its sensitivity based on your skin tone to account for normal ' +
          'variation. These checks are screening signals, not diagnostic.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If a dark band is longstanding and unchanged, it is very likely harmless. If it is new, ' +
          'widening, or changing color or shape, or if you are unsure how long you\'ve had it, ' +
          'show it to a doctor — they can examine it and decide if further testing is needed.',
      },
    ],
  },
  {
    key: 'pallor',
    icon: 'info',
    name: 'Pallor (pale nails)',
    summary: 'An unusually pale or white nail bed.',
    lead:
      'Most nails have a pink nail bed with a white tip. When the nail bed is unusually pale ' +
      'or white instead, it can sometimes relate to low blood iron, anemia, liver disease, or ' +
      'kidney issues — but it can also be normal variation.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'The nail bed (the part under the transparent nail plate) looks pale, whitish, or almost ' +
          'colorless instead of the typical pink color. The very tip of the nail may still be white, ' +
          'but the middle and base look less pink than usual.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Pale nails can relate to low red blood cell count (anemia), low iron, liver disease, ' +
          'kidney disease, or reduced blood flow to the fingers. They can also just be a normal ' +
          'variation in skin tone. A doctor needs to examine you and possibly run blood tests to ' +
          'figure out what\'s causing it.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We analyze the nail bed color from a top-down photo and look for paleness or whitening, ' +
          'adjusting for your skin tone. This is a screening signal only — it is not a measure of ' +
          'blood counts or oxygen levels.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'Widespread pale nails, especially across multiple fingers, are worth mentioning to a ' +
          'doctor during an exam. If you also feel tired, dizzy, or short of breath, mention those ' +
          'symptoms too — they may help your doctor decide if blood work is needed.',
      },
    ],
  },
  {
    key: 'cyanosis',
    icon: 'sparkle',
    name: 'Cyanosis (bluish nails)',
    summary: 'A bluish or purple tint to the nails.',
    lead:
      'When nails have a bluish or purple tint instead of the usual pink and white, it is called ' +
      'cyanosis. This can relate to low oxygen in the blood, cold exposure, or heart/lung problems — ' +
      'but it can also be a camera artifact or lighting effect.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'The nail bed and nail plate have a bluish, purplish, or grayish tint instead of the ' +
          'typical pink color. The discoloration may involve the whole nail or be most noticeable ' +
          'in the nail bed.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'True cyanosis (a bluish tint from low blood oxygen) can happen with lung disease, heart ' +
          'disease, or severe cold exposure. Nails can also look blue or purple from bruising, old ' +
          'age, cold fingers, or certain medications. Nail fungus can sometimes cause a bluish tint ' +
          'too.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We analyze the color of the nail bed and plate from a top-down photo and look for bluish ' +
          'or purple hues. Be aware that lighting, phone camera white-balance, and nail polish can ' +
          'affect this — these checks are screening signals, not an oxygen measurement.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If your nails look genuinely bluish and you also notice shortness of breath, chest pain, ' +
          'or your lips or tongue look blue, seek medical attention right away. If nails just look ' +
          'slightly blue on photos but you feel fine, it may be a camera artifact — a doctor can ' +
          'examine your nails in person to clarify.',
      },
    ],
  },
  {
    key: 'terrys_nails',
    icon: 'clipboard',
    name: 'Terry\'s nails',
    summary: 'Most of the nail white or opaque with a narrow dark band at the tip.',
    lead:
      'In Terry\'s nails, the nail bed looks mostly white or opaque, leaving only a narrow ' +
      'reddish-brown or dark band at the very tip. This pattern is often tied to liver disease, ' +
      'heart failure, kidney disease, or diabetes.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'Most of the nail (roughly two-thirds to three-quarters) looks white, opaque, or pale. ' +
          'Just the distal tip shows a distinct darker reddish-brown band, usually 1-3mm wide. ' +
          'Sometimes a thin pale line separates the white area from the dark band.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Terry\'s nails are most often seen with liver disease, kidney disease, heart failure, ' +
          'or diabetes. They can also show up after chemotherapy or with aging. The exact cause is ' +
          'not fully understood, but the nail bed changes in a way that makes it appear whiter. ' +
          'It is considered a clinical sign worth investigating.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We estimate the nail plate and look for a sharp transition between a mostly white nail ' +
          'bed and a darker distal band. This is a screening signal — proper diagnosis requires a ' +
          'doctor\'s examination.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If your nails match this pattern, especially across multiple fingers, it is worth showing ' +
          'to a doctor. They can check your overall health and may order tests (blood work, liver ' +
          'function, kidney function, heart exam) to understand what\'s going on.',
      },
    ],
  },
  {
    key: 'lindsays_nails',
    icon: 'clipboard',
    name: 'Half-and-half nails (Lindsay\'s nails)',
    summary: 'Proximal half white, distal half reddish-brown.',
    lead:
      'In Lindsay\'s nails, there is a sharp line across the middle of the nail: the half closer ' +
      'to the cuticle is white or pale, and the half toward the tip is reddish-brown or pink. ' +
      'This pattern is often associated with kidney disease.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'A horizontal line divides the nail roughly in half: the proximal half (near the cuticle) ' +
          'is white, opaque, or pale, and the distal half (toward the tip) is reddish, pink, or ' +
          'brown. The demarcation line is usually sharp and distinct.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Lindsay\'s nails are classically associated with kidney disease and kidney failure, ' +
          'especially in patients on dialysis. They can also occur with other serious illnesses like ' +
          'liver disease or leukemia. The exact cause is unknown, but the pattern is considered a ' +
          'clinical sign worth investigating.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We estimate the nail boundaries and look for a clear horizontal band separating a white ' +
          'proximal half from a darker distal half. This is a screening signal based on color and ' +
          'positioning.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If your nails show this pattern, especially across multiple fingers, bring it to a ' +
          'doctor\'s attention. If you have any history of kidney problems, diabetes, or liver ' +
          'disease, mention that too — your doctor can order appropriate tests and follow-up.',
      },
    ],
  },
  {
    key: 'onycholysis',
    icon: 'finger',
    name: 'Onycholysis (nail lifting)',
    summary: 'The nail separating from the bed, looking opaque at the free edge.',
    lead:
      'Onycholysis is when the nail begins to separate from the underlying nail bed, starting at ' +
      'the free edge and working backward toward the cuticle. The separated part looks opaque or ' +
      'white instead of the clear color it would have if still attached.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'The nail lifts away from the finger starting at the tip and potentially extending back ' +
          'toward the cuticle. The lifted area looks opaque, whitish, or chalky instead of clear. ' +
          'You may be able to see air or debris under the nail in the lifted area.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Onycholysis can be caused by nail trauma, thyroid disease (especially hyperthyroidism), ' +
          'psoriasis, fungal infection, contact dermatitis, or reactions to medications or nail ' +
          'products. Sometimes the cause is never found. It usually grows out as the nail replaces ' +
          'itself, but treatment depends on the underlying cause.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We look for areas where the nail appears to separate or lift from the finger, showing as ' +
          'opaque or white zones especially at or near the free edge. This is a visual screening ' +
          'check only.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If you notice nail lifting, keep the area dry and clean to prevent infection, and avoid ' +
          'aggressive manicuring or exposure to harsh chemicals. Show it to a doctor if it spreads ' +
          'quickly, gets painful, or if you develop signs of infection. Your doctor can test for ' +
          'thyroid disease, psoriasis, or fungus if needed.',
      },
    ],
  },
  {
    key: 'beaus_lines',
    icon: 'clipboard',
    name: 'Beau\'s lines',
    summary: 'Horizontal grooves or indentations across the nail.',
    lead:
      'Beau\'s lines are grooves or indentations that run across the width of the nail, from side ' +
      'to side. They mark a temporary pause or slowdown in nail growth, usually caused by illness, ' +
      'high fever, surgery, or severe stress.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'One or more horizontal grooves or ridges run across the entire width of the nail from one ' +
          'side to the other. The grooves can be shallow or quite deep, and may be more visible on ' +
          'some fingers than others.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Beau\'s lines form when the nail-growing cells pause or slow down, which happens after ' +
          'significant physical or emotional stress — a high fever, serious illness, surgery, severe ' +
          'infection, or major injury. They appear roughly in the area of the nail that was growing ' +
          'at the time of the stress. As the nail grows out, the line slowly moves toward the tip ' +
          'and eventually disappears.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We analyze the nail surface for horizontal indentations or grooves that run across the ' +
          'width. This is a visual screening check based on surface texture.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If you notice Beau\'s lines, try to recall if you had a significant illness, high fever, ' +
          'surgery, or major stress about 6-12 weeks earlier — the timeline usually matches. Beau\'s ' +
          'lines themselves are harmless and fade as the nail grows out. If you have recurring lines ' +
          'or other concerning nail changes, mention them to a doctor.',
      },
    ],
  },
  {
    key: 'muehrckes_lines',
    icon: 'clipboard',
    name: 'Muehrcke\'s lines',
    summary: 'Paired white bands across the nail that do not move as the nail grows.',
    lead:
      'Muehrcke\'s lines are pairs of white bands that run horizontally across the nail. Unlike ' +
      'Beau\'s lines, they stay in the same position relative to the cuticle as the nail grows — ' +
      'they don\'t move toward the tip. They often relate to low blood protein or kidney disease.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'Two white bands run horizontally across the nail, usually in the middle or proximal region. ' +
          'The bands are separated by a thin line of normal nail color. Unlike Beau\'s lines (grooves), ' +
          'Muehrcke\'s lines are flat (no indentation) — they are purely a color change.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Muehrcke\'s lines are classically associated with low blood protein (hypoalbuminemia), which ' +
          'can happen with kidney disease, liver disease, malnutrition, or other serious illnesses. They ' +
          'can also show up temporarily during pregnancy or with certain cancers. The lines reflect a ' +
          'change in the nail bed itself and stay in place as the nail grows (unlike Beau\'s lines, which ' +
          'move toward the tip).',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We look for paired horizontal white bands on the nail that are flat (not grooved) and stay in ' +
          'roughly the same position across the nail width. This is a visual screening check.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If you notice this pattern, especially on multiple nails, bring it to a doctor. It often ' +
          'points to a kidney or liver issue that deserves investigation. Your doctor can order blood ' +
          'tests to check protein levels, kidney function, and liver function.',
      },
    ],
  },
  {
    key: 'splinter_hemorrhages',
    icon: 'search',
    name: 'Splinter hemorrhages',
    summary: 'Tiny dark streaks under the nail running lengthwise.',
    lead:
      'Splinter hemorrhages are small dark red, brown, or black streaks that run lengthwise under ' +
      'the nail. They look like tiny splinters of wood. Most are caused by minor trauma, but they ' +
      'can occasionally relate to infections or other conditions.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'One or more thin, dark (red, brown, or black) streaks run lengthwise under the nail, from ' +
          'the nail bed toward the tip. They look like tiny splinters, usually a few millimeters long. ' +
          'They are most noticeable in the middle or distal portions of the nail.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Most splinter hemorrhages come from minor bumps or trauma to the finger that damage small ' +
          'blood vessels under the nail. They heal on their own as the nail grows out. Occasionally, ' +
          'they can be a sign of a blood infection (endocarditis), especially if they appear on multiple ' +
          'nails without any obvious injury, or if they appear alongside other symptoms like fever, ' +
          'chills, or a new heart murmur.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We look for dark longitudinal streaks under the nail that could indicate small hemorrhages. ' +
          'This is a visual screening check — some dark lines could be artifacts from dirt or the phone ' +
          'camera.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If you see a splinter hemorrhage and remember hitting your finger, it will likely fade on its ' +
          'own. If multiple nails develop splinter hemorrhages without any injury, or if you also have ' +
          'fever or feel ill, mention it to a doctor — they can evaluate whether further testing is needed.',
      },
    ],
  },
  {
    key: 'pitting',
    icon: 'eye',
    name: 'Nail pitting',
    summary: 'Small dents or pinpricks in the nail surface.',
    lead:
      'Nail pitting is the appearance of small dents, pits, or pinpricks scattered across the nail ' +
      'surface. Pitting is frequently seen with psoriasis, but can also show up with alopecia, ' +
      'connective tissue disease, or sometimes on its own.',
    points: [
      {
        icon: 'eye',
        title: 'What it looks like',
        text:
          'The nail surface has multiple small round or irregular indentations, like tiny pits or ' +
          'dents scattered across the nail. The pits can be shallow or deeper, and may involve just ' +
          'the surface or extend partially into the nail. They give the nail a rougher appearance.',
      },
      {
        icon: 'pulse',
        title: 'Why it happens',
        text:
          'Pitting is most commonly linked to psoriasis (a skin condition) and alopecia areata ' +
          '(patchy hair loss). It can also occur with connective tissue diseases, fungal infections, ' +
          'or sometimes on its own without any other cause. Psoriasis-related pitting often involves ' +
          'multiple nails.',
      },
      {
        icon: 'camera',
        title: 'How NailIQ checks it',
        text:
          'We analyze the nail surface for small indentations and pitting patterns. This is a visual ' +
          'screening check based on surface texture, though camera resolution and lighting can affect ' +
          'how visible fine pits are.',
      },
      {
        icon: 'checkCircle',
        title: 'What to do with your result',
        text:
          'If you notice pitting on multiple nails, it is worth mentioning to a doctor, especially if ' +
          'you also have skin symptoms like patches or itching, or hair loss. Your doctor can examine ' +
          'you and decide if testing or further evaluation is needed.',
      },
    ],
  },
]

function ConditionSheet({ condition, onClose }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={condition.name}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-handle" aria-hidden="true" />

        <header className="sheet-header">
          <span className="sheet-header-icon">
            <Icon name={condition.icon} size={22} />
          </span>
          <div className="sheet-header-text">
            <h2 className="sheet-title">{condition.name}</h2>
            <p className="sheet-subtitle">{condition.summary}</p>
          </div>
          <button type="button" className="sheet-close" onClick={onClose} aria-label="Close">
            <Icon name="x" size={22} />
          </button>
        </header>

        <div className="sheet-body">
          {condition.lead && <p className="sheet-lead">{condition.lead}</p>}

          {['clubbing', 'koilonychia'].includes(condition.key) && (
            <div className="diagram-wrap">
              <NailDiagram type={condition.key} />
            </div>
          )}

          {condition.points.map((point) => (
            <div key={point.title} className="info-point">
              <span className="info-point-icon">
                <Icon name={point.icon} />
              </span>
              <div>
                <p className="info-point-title">{point.title}</p>
                <p className="info-point-text">{point.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function InfoSection() {
  const [openKey, setOpenKey] = useState(null)
  const openCondition = CONDITIONS.find((c) => c.key === openKey) ?? null

  return (
    <div className="info-section">
      {CONDITIONS.map((condition) => (
        <button
          key={condition.key}
          type="button"
          className="info-card"
          onClick={() => setOpenKey(condition.key)}
        >
          <span className="info-icon">
            <Icon name={condition.icon} />
          </span>
          <span className="info-summary-text">
            <span className="info-name">{condition.name}</span>
            <span className="info-blurb">{condition.summary}</span>
          </span>
          <span className="info-chevron">
            <Icon name="chevronRight" size={18} />
          </span>
        </button>
      ))}

      {openCondition && (
        <ConditionSheet condition={openCondition} onClose={() => setOpenKey(null)} />
      )}
    </div>
  )
}
