// the actual copy for each condition lives in the locale dictionaries under `conditions.<key>`
export const CONDITION_KEYS = [
  'clubbing',
  'koilonychia',
  'leukonychia',
  'melanonychia',
  'pallor',
  'cyanosis',
  'terrys_nails',
  'lindsays_nails',
  'onycholysis',
  'beaus_lines',
  'muehrckes_lines',
  'splinter_hemorrhages',
  'pitting',
  'onychogryphosis',
]

const CONDITION_ICONS = {
  clubbing: 'finger',
  koilonychia: 'spoon',
  leukonychia: 'sparkle',
  melanonychia: 'search',
  pallor: 'info',
  cyanosis: 'sparkle',
  terrys_nails: 'clipboard',
  lindsays_nails: 'clipboard',
  onycholysis: 'finger',
  beaus_lines: 'clipboard',
  muehrckes_lines: 'clipboard',
  splinter_hemorrhages: 'search',
  pitting: 'eye',
  onychogryphosis: 'finger',
}

const POINT_ORDER = [
  { id: 'looks', icon: 'eye' },
  { id: 'why', icon: 'pulse' },
  { id: 'how', icon: 'camera' },
  { id: 'action', icon: 'checkCircle' },
]

export function getConditions(t) {
  return CONDITION_KEYS.map((key) => ({
    key,
    icon: CONDITION_ICONS[key],
    name: t(`conditions.${key}.name`),
    summary: t(`conditions.${key}.summary`),
    lead: t(`conditions.${key}.lead`),
    points: POINT_ORDER.map(({ id, icon }) => ({
      icon,
      title: t(`pointTitles.${id}`),
      text: t(`conditions.${key}.points.${id}`),
    })),
  }))
}

export function conditionSummary(t, label) {
  const key = `conditions.${label}.summary`
  const text = t(key)
  return text === key ? null : text
}

export function conditionNextStep(t, label) {
  const key = `conditions.${label}.points.action`
  const text = t(key)
  return text === key ? null : text
}
