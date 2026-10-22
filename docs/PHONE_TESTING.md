# Testing NailIQ on an iPhone (home Wi-Fi, HTTPS)

iOS only allows the camera on HTTPS pages, so the dev server runs with a local certificate. A Cloudflare tunnel was tried
first and abandoned: on the district laptop it exited about a minute after start (cause not confirmed).

**On the PC** (in a PowerShell window, repo root; keep it open):
`$env:PHONE_HTTPS = '1'; $env:PORT = '8443'; npm --prefix frontend run dev`
-> serves https://<PC Wi-Fi IP>:8443 (port 5174 was blocked by something else on this PC). `dev-with-backend.mjs` also starts the backend on :5000 if it is not running. The PC IP is in the certificate (192.168.1.35); if it changes, regenerate `data/phone_test_certs` (openssl: name-constrained CA, server cert with `subjectAltName=IP:<ip>`, then delete the CA key).

**One-time on the iPhone** (same Wi-Fi):
1. Safari: open `https://192.168.1.35:8443/nailiq-ca.crt` (Safari will warn the page is not private; continue for this one file) -> Allow the profile download.
2. Settings -> "Profile Downloaded" -> Install ("NailIQ local dev CA").
3. Settings -> General -> About -> Certificate Trust Settings -> turn ON "NailIQ local dev CA".
4. Safari: open `https://192.168.1.35:8443/` (no warning now). Share -> Add to Home Screen. Open NailIQ from the icon; allow the camera.

If the page does not load: Windows Firewall may be blocking Node on the "Public" network (this Wi-Fi is classed Public). Allow `node.exe` when Windows asks, or set the network to Private in Windows settings. The phone and PC must be on the same Wi-Fi (not the guest network).

Security: the CA is limited to 192.168.1.0/24 and localhost (name constraints) and its private key was deleted after signing the server cert, so it cannot sign anything else. Remove it from the phone afterwards (Settings -> General -> VPN & Device Management). Certs are valid 365 days and are gitignored.

Checklist: onboarding scroll, Settings open/close, both photos with the real camera (alignment frame), results scroll, History, Learn, rotate the phone, large text / high contrast, every language.
