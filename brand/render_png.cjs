// Renders the SVGs in this folder to PNGs (needs `playwright` installed globally). Run: node brand/render_png.cjs
const path = require('path')
const fs = require('fs')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const dir = __dirname
const read = (f) => fs.readFileSync(path.join(dir, f), 'utf8')
;(async () => {
  const b = await chromium.launch()
  const shot = async (file, w, h, out, bg) => {
    const p = await b.newPage({ viewport: { width: w, height: h } })
    await p.setContent(`<body style="margin:0;background:${bg ?? 'transparent'}"><div style="width:${w}px;height:${h}px">${read(file).replace(/width="\d+" height="\d+"/, 'width="100%" height="100%"')}</div></body>`)
    await p.screenshot({ path: path.join(dir, out), omitBackground: !bg })
    await p.close()
  }
  await shot('app-icon.svg', 1024, 1024, 'app-icon-1024.png')
  await shot('app-icon.svg', 512, 512, 'app-icon-512.png')
  await shot('app-icon.svg', 192, 192, 'app-icon-192.png')
  await shot('favicon.svg', 64, 64, 'favicon-64.png')
  await shot('favicon.svg', 32, 32, 'favicon-32.png')
  await shot('logo-mark.svg', 512, 512, 'logo-mark-512.png')
  await shot('logo-lockup.svg', 1408, 480, 'logo-lockup-1408.png')
  await shot('logo-lockup-light.svg', 1408, 480, 'logo-lockup-light-1408.png')

  // preview sheet
  const p = await b.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 1 })
  const inline = (f, w, h) => read(f).replace(/width="\d+" height="\d+"/, `width="${w}" height="${h}"`)
  await p.setContent(`<body style="margin:0;font-family:Segoe UI,sans-serif">
   <div style="display:grid;grid-template-columns:1fr 1fr;height:520px">
     <div style="background:#0b0c0e;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:40px">${inline('logo-lockup.svg', 520, 177)}${inline('logo-mark.svg', 150, 150)}</div>
     <div style="background:#f2f6f4;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:40px">${inline('logo-lockup-light.svg', 520, 177)}${inline('logo-mark-light.svg', 150, 150)}</div>
   </div>
   <div style="background:#1b1d20;height:380px;display:flex;align-items:center;justify-content:center;gap:48px;color:#8a9094;font-size:14px">
     <div style="text-align:center">${inline('app-icon.svg', 220, 220)}<br>app icon</div>
     <div style="text-align:center">${inline('app-icon.svg', 120, 120)}<br>120</div>
     <div style="text-align:center">${inline('app-icon.svg', 60, 60)}<br>60</div>
     <div style="text-align:center">${inline('favicon.svg', 32, 32)}<br>favicon 32</div>
     <div style="text-align:center;background:#fff;padding:14px 18px;border-radius:12px">${inline('logo-mark-light.svg', 28, 28)}<br><span style="color:#555">28 on white</span></div>
   </div></body>`)
  await p.screenshot({ path: path.join(dir, 'preview.png') })
  await b.close()
})()
