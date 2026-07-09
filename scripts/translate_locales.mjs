// Machine-translates the frontend locale dictionaries via the DeepL API.
//
// Reads frontend/src/i18n/en.js as the source of truth, finds keys missing from
// each target locale (or generates the whole file if it doesn't exist), batch-
// translates them, and writes the locale file back. {placeholders} are protected
// as <ph> XML tags so DeepL passes them through untouched.
//
// Output is MACHINE TRANSLATION — always review before shipping (medical copy,
// non-diagnostic hedging, and formal/informal register are where MT goes wrong).
//
// Usage:
//   node scripts/translate_locales.mjs pt vi ko    # one or more locale codes
//
// Needs DEEPL_API_KEY in the environment or in .env at the repo root.

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const I18N_DIR = path.join(ROOT, 'frontend', 'src', 'i18n')
const API_URL = 'https://api-free.deepl.com/v2/translate'
const BATCH_SIZE = 50 // DeepL max texts per request

// locale code (= file name and <html lang>) -> DeepL target + native name.
// Add a language: add a row here, run the script, review, register in index.jsx.
const TARGETS = {
  pt: { deepl: 'PT-BR', langName: 'Português' },
  fr: { deepl: 'FR', langName: 'Français' },
  vi: { deepl: 'VI', langName: 'Tiếng Việt' },
  ko: { deepl: 'KO', langName: '한국어' },
  ru: { deepl: 'RU', langName: 'Русский' },
  ja: { deepl: 'JA', langName: '日本語' },
  de: { deepl: 'DE', langName: 'Deutsch' },
  it: { deepl: 'IT', langName: 'Italiano' },
  id: { deepl: 'ID', langName: 'Bahasa Indonesia' },
  tr: { deepl: 'TR', langName: 'Türkçe' },
}

function loadApiKey() {
  if (process.env.DEEPL_API_KEY) return process.env.DEEPL_API_KEY
  const envPath = path.join(ROOT, '.env')
  if (existsSync(envPath)) {
    const match = readFileSync(envPath, 'utf8').match(/^DEEPL_API_KEY=(.+)$/m)
    if (match) return match[1].trim()
  }
  console.error('DEEPL_API_KEY not found (env var or .env at repo root).')
  process.exit(1)
}

// --- flatten / unflatten (arrays use numeric path segments) ------------------

function flatten(node, prefix = '', out = new Map()) {
  if (typeof node === 'string') {
    out.set(prefix, node)
  } else if (Array.isArray(node)) {
    node.forEach((v, i) => flatten(v, `${prefix}.${i}`, out))
  } else if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      flatten(v, prefix ? `${prefix}.${k}` : k, out)
    }
  }
  return out
}

function unflatten(map) {
  const root = {}
  for (const [pathKey, value] of map) {
    const parts = pathKey.split('.')
    let node = root
    for (let i = 0; i < parts.length - 1; i++) {
      const key = parts[i]
      if (!(key in node)) node[key] = /^\d+$/.test(parts[i + 1]) ? [] : {}
      node = node[key]
    }
    node[parts[parts.length - 1]] = value
  }
  return root
}

// --- placeholder protection ---------------------------------------------------

// XML-escape first (bare & / < break DeepL's tag parser), then wrap
// {placeholders} in <ph> tags so they pass through untranslated.
const encodePlaceholders = (s) =>
  s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/\{(\w+)\}/g, '<ph>$1</ph>')
const decodePlaceholders = (s) =>
  s
    .replace(/<ph>(\w+)<\/ph>/g, '{$1}')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')

// --- DeepL ---------------------------------------------------------------------

async function translateBatch(apiKey, texts, targetLang) {
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: {
      Authorization: `DeepL-Auth-Key ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: texts,
      source_lang: 'EN',
      target_lang: targetLang,
      tag_handling: 'xml',
      ignore_tags: ['ph'],
    }),
  })
  if (!res.ok) {
    throw new Error(`DeepL ${res.status}: ${await res.text()}`)
  }
  const data = await res.json()
  return data.translations.map((t) => t.text)
}

// --- main ----------------------------------------------------------------------

async function main() {
  const codes = process.argv.slice(2)
  if (codes.length === 0) {
    console.error(`Usage: node scripts/translate_locales.mjs <code>...\nKnown codes: ${Object.keys(TARGETS).join(', ')}`)
    process.exit(1)
  }
  const apiKey = loadApiKey()

  const en = (await import(pathToFileURL(path.join(I18N_DIR, 'en.js')).href)).default
  const enFlat = flatten(en)
  enFlat.delete('langName') // never translated; set from TARGETS

  for (const code of codes) {
    const target = TARGETS[code]
    if (!target) {
      console.error(`Unknown code "${code}" — add it to TARGETS first.`)
      continue
    }

    const filePath = path.join(I18N_DIR, `${code}.js`)
    const existingFlat = existsSync(filePath)
      ? flatten((await import(pathToFileURL(filePath).href)).default)
      : new Map()

    const missing = [...enFlat.keys()].filter((k) => !existingFlat.has(k))
    if (missing.length === 0) {
      console.log(`${code}: up to date (${existingFlat.size} keys)`)
      continue
    }
    console.log(`${code}: translating ${missing.length} keys -> ${target.deepl}`)

    const translated = new Map()
    for (let i = 0; i < missing.length; i += BATCH_SIZE) {
      const chunk = missing.slice(i, i + BATCH_SIZE)
      const results = await translateBatch(
        apiKey,
        chunk.map((k) => encodePlaceholders(enFlat.get(k))),
        target.deepl,
      )
      chunk.forEach((k, j) => translated.set(k, decodePlaceholders(results[j])))
      console.log(`  ${Math.min(i + BATCH_SIZE, missing.length)}/${missing.length}`)
    }

    // Rebuild in en.js key order so the file diffs cleanly against the master.
    const merged = new Map([['langName', target.langName]])
    for (const key of enFlat.keys()) {
      merged.set(key, existingFlat.get(key) ?? translated.get(key))
    }

    const header =
      `// ${target.langName} translations. Keys mirror en.js; missing keys fall back to English.\n` +
      `// MACHINE-TRANSLATED via DeepL (scripts/translate_locales.mjs) — review before shipping.\n`
    writeFileSync(filePath, `${header}export default ${JSON.stringify(unflatten(merged), null, 2)}\n`)
    console.log(`${code}: wrote ${filePath}`)
  }
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
