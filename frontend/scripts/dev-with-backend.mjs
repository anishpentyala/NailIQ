import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..", "..");
const backendDir = path.join(projectRoot, "backend");
// process.env.PORT is set by the dev-server harness for Vite's own autoPort
// assignment - the backend must NOT inherit it, or both servers race for the
// same port. The backend gets its own port via BACKEND_PORT instead.
const backendPort = Number(process.env.BACKEND_PORT) || 5000;

function isPortListening(port) {
  return new Promise((resolve) => {
    const socket = net.connect({ port, host: "127.0.0.1" });
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.once("error", () => resolve(false));
  });
}

let backend = null;

async function startBackend() {
  if (await isPortListening(backendPort)) {
    console.log(`[dev] backend already running on :${backendPort}, leaving it alone`);
    return;
  }

  const pythonExe = process.platform === "win32"
    ? path.join(backendDir, "venv", "Scripts", "python.exe")
    : path.join(backendDir, "venv", "bin", "python");

  console.log("[dev] starting backend...");
  backend = spawn(pythonExe, ["app.py"], {
    cwd: backendDir,
    stdio: "inherit",
    env: { ...process.env, PORT: String(backendPort) },
  });

  backend.on("exit", (code) => {
    if (code !== null && code !== 0) {
      console.error(`[dev] backend exited with code ${code}`);
    }
    backend = null;
  });
}

function stopBackend() {
  if (backend) {
    backend.kill();
    backend = null;
  }
}

await startBackend();

const vite = spawn("npx", ["vite", ...process.argv.slice(2)], {
  cwd: path.join(projectRoot, "frontend"),
  stdio: "inherit",
  shell: process.platform === "win32",
  env: process.env,
});

vite.on("exit", (code) => {
  stopBackend();
  process.exit(code ?? 0);
});

process.on("SIGINT", () => {
  vite.kill();
  stopBackend();
  process.exit(0);
});

process.on("SIGTERM", () => {
  vite.kill();
  stopBackend();
  process.exit(0);
});
