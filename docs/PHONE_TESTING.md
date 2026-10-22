# Testing NailIQ on an iPhone

1. On the PC (repo root): `powershell -ExecutionPolicy Bypass -File scripts\phone_test.ps1` - starts the backend, the frontend and a Cloudflare quick tunnel, then prints an `https://....trycloudflare.com` link (new every run).
2. On the iPhone, open the link in **Safari**. Share -> **Add to Home Screen**. Open NailIQ from the new icon (full screen, no Safari bars). Allow the camera.
3. Stop everything: `powershell -ExecutionPolicy Bypass -File scripts\phone_test.ps1 -Stop`.

Notes: the PC must stay on and awake. The camera needs HTTPS, which the tunnel provides. Anyone with the link can use the running app (and see its scan history) until you stop it. Logs: `data/phone_test_logs/`.

Checklist: onboarding scroll, Settings open/close, both photos with the real camera (alignment frame), results scroll, History, Learn, rotate the phone, large text / high contrast, every language.
