/* eslint-disable react-refresh/only-export-components -- provider module:
   exports the provider plus its hook/helpers by design */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import en from './en'
import es from './es'
import zh from './zh'
import hi from './hi'
import fr from './fr'
import pt from './pt'

// add a language: import its dictionary and list it here
const DICTIONARIES = { en, es, zh, hi, fr, pt }
export const LANGUAGES = Object.entries(DICTIONARIES).map(([code, dict]) => ({
  code,
  name: dict.langName,
}))

const STORAGE_KEY = 'nailiq-settings'

const DEFAULTS = {
  lang: null, // null = follow the browser language on first visit
  highContrast: false,
  largeText: false,
  reduceMotion: false,
  darkMode: null, // null = follow the OS color-scheme preference
}

function loadStored() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') }
  } catch {
    return { ...DEFAULTS }
  }
}

function systemPrefersDark() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

function browserLang() {
  const preferred = (navigator.languages ?? [navigator.language ?? 'en']).map((l) =>
    l.slice(0, 2).toLowerCase(),
  )
  return preferred.find((l) => l in DICTIONARIES) ?? 'en'
}

function lookup(dict, path) {
  let node = dict
  for (const part of path.split('.')) {
    if (node == null || typeof node !== 'object') return undefined
    node = node[part]
  }
  return node
}

const SettingsContext = createContext(null)

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(loadStored)
  const [systemDark, setSystemDark] = useState(systemPrefersDark)
  const lang = settings.lang ?? browserLang()
  const isDark = settings.darkMode ?? systemDark

  // keep dark mode in sync if the user flips their OS theme mid-session
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!mq) return
    const onChange = (e) => setSystemDark(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const update = useCallback((patch) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      } catch {
        // storage might be unavailable, settings still work for this session
      }
      return next
    })
  }, [])

  // Reflect the settings onto <html> so CSS (and screen readers, via lang) see them.
  useEffect(() => {
    const root = document.documentElement
    root.lang = lang
    root.classList.toggle('a11y-contrast', settings.highContrast)
    root.classList.toggle('a11y-large-text', settings.largeText)
    root.classList.toggle('a11y-reduce-motion', settings.reduceMotion)
    root.classList.toggle('theme-dark', isDark)
  }, [lang, settings.highContrast, settings.largeText, settings.reduceMotion, isDark])

  const t = useCallback(
    (key, params) => {
      let value = lookup(DICTIONARIES[lang], key)
      if (value === undefined) value = lookup(en, key)
      if (value === undefined) return key
      if (typeof value !== 'string') return value // arrays (e.g. home.tips)
      if (params) {
        value = value.replace(/\{(\w+)\}/g, (match, name) =>
          params[name] !== undefined ? String(params[name]) : match,
        )
      }
      return value
    },
    [lang],
  )

  const ctx = useMemo(
    () => ({
      t,
      lang,
      setLang: (code) => update({ lang: code }),
      highContrast: settings.highContrast,
      largeText: settings.largeText,
      reduceMotion: settings.reduceMotion,
      darkMode: isDark,
      setPref: (name, on) => update({ [name]: on }),
    }),
    [t, lang, settings.highContrast, settings.largeText, settings.reduceMotion, isDark, update],
  )

  return <SettingsContext.Provider value={ctx}>{children}</SettingsContext.Provider>
}

export function useI18n() {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useI18n must be used inside <SettingsProvider>')
  return ctx
}

// use the localized name if we have one, otherwise fall back to what the backend sent
export function findingName(t, finding) {
  if (finding.track_used === 'appearance') return t(`crop.${finding.label}`)
  const localized = t(`findingNames.${finding.label}`)
  return localized === `findingNames.${finding.label}` ? finding.display_name : localized
}
