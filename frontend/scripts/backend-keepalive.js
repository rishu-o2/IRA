const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");

const BACKEND_URL = "http://127.0.0.1:8765/health";
const CHECK_INTERVAL_MS = 2500;
const RESTART_DELAY_MS = 1200;

let backendProcess = null;
let starting = false;

function checkBackend() {
  return new Promise((resolve) => {
    const request = http.get(BACKEND_URL, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });

    request.on("error", () => resolve(false));
    request.setTimeout(900, () => {
      request.destroy();
      resolve(false);
    });
  });
}

function findPythonExecutable() {
  const candidates = [
    process.env.IRA_PYTHON,
    process.env.PYTHON,
    path.join(process.env.LOCALAPPDATA || "", "Python", "pythoncore-3.14-64", "python.exe"),
    path.join(process.env.LOCALAPPDATA || "", "Python", "pythoncore-3.14-64", "pythonw.exe"),
    "py",
    "python",
  ].filter(Boolean);

  return candidates.find((candidate) => candidate === "py" || candidate === "python" || fs.existsSync(candidate));
}

async function startBackend() {
  if (starting || backendProcess || (await checkBackend())) {
    return;
  }

  starting = true;
  const python = findPythonExecutable();

  if (!python) {
    console.error("[IRA] Could not find Python. Set IRA_PYTHON to your python.exe path.");
    starting = false;
    return;
  }

  const backendDir = path.resolve(__dirname, "..", "..", "backend");
  const args = python === "py" ? ["-3", "-m", "ira.server"] : ["-m", "ira.server"];

  console.log("[IRA] Starting backend on port 8765...");
  backendProcess = spawn(python, args, {
    cwd: backendDir,
    stdio: "ignore",
    windowsHide: true,
    shell: false,
  });

  backendProcess.on("exit", (code) => {
    console.log(`[IRA] Backend exited with code ${code}. Restarting soon.`);
    backendProcess = null;
    windowlessDelay(RESTART_DELAY_MS).then(() => {
      starting = false;
      startBackend();
    });
  });

  backendProcess.on("error", (error) => {
    console.error("[IRA] Backend start failed:", error.message);
    backendProcess = null;
    starting = false;
  });

  for (let attempt = 0; attempt < 24; attempt += 1) {
    if (await checkBackend()) {
      console.log("[IRA] Backend is ready.");
      starting = false;
      return;
    }
    await windowlessDelay(500);
  }

  console.error("[IRA] Backend did not become ready.");
  starting = false;
}

function windowlessDelay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function monitor() {
  if (!(await checkBackend())) {
    await startBackend();
  }
}

startBackend();
setInterval(monitor, CHECK_INTERVAL_MS);

process.on("SIGINT", () => {
  if (backendProcess) {
    backendProcess.kill("SIGINT");
  }
  process.exit();
});
