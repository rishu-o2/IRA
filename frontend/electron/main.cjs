const { app, BrowserWindow, session } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

app.commandLine.appendSwitch("enable-experimental-web-platform-features");
app.commandLine.appendSwitch("disable-gpu-shader-disk-cache");
app.commandLine.appendSwitch("disable-gpu-program-cache");

const isDev = !app.isPackaged;

// Get the local dev server URL
const getDevServerURL = () => {
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl && devUrl.trim()) return devUrl.trim();
  
  // Always use localhost for dev - it's accessible from the same machine
  return "http://localhost:5173";
};

const devServerURL = getDevServerURL();
let backendProcess = null;

const allowMediaPermission = (permission) => {
  return ["camera", "microphone", "media", "videoCapture", "audioCapture"].includes(permission);
};

function setupPermissions() {
  const checker = (webContents, permission) => {
    if (allowMediaPermission(permission)) {
      console.log(`[IRA] Granting permission: ${permission}`);
      return true;
    }
    return false;
  };

  const requester = (webContents, permission, callback) => {
    if (allowMediaPermission(permission)) {
      console.log(`[IRA] Auto-granting requested permission: ${permission}`);
      callback(true);
      return;
    }
    callback(false);
  };

  session.defaultSession.setPermissionCheckHandler(checker);
  session.defaultSession.setPermissionRequestHandler(requester);
}

function checkBackend() {
  return new Promise((resolve) => {
    const request = http.get("http://127.0.0.1:8765/health", (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });

    request.on("error", () => resolve(false));
    request.setTimeout(800, () => {
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
    "py",
    "python"
  ].filter(Boolean);

  return candidates.find((candidate) => candidate === "py" || candidate === "python" || fs.existsSync(candidate));
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function startBackend() {
  if (await checkBackend()) {
    console.log("[IRA] Reusing existing backend on port 8765.");
    return true;
  }

  const python = findPythonExecutable();
  if (!python) {
    console.warn("[IRA] Could not find Python to start the backend.");
    return false;
  }

  const backendDir = path.resolve(__dirname, "..", "..", "backend");
  const args = python === "py" ? ["-3", "-m", "ira.server"] : ["-m", "ira.server"];

  backendProcess = spawn(python, args, {
    cwd: backendDir,
    windowsHide: true,
    stdio: "ignore"
  });

  backendProcess.on("exit", (code) => {
    console.log(`[IRA] Backend process exited with code ${code}.`);
    backendProcess = null;
  });

  backendProcess.on("error", (error) => {
    console.warn("[IRA] Backend failed to start:", error.message);
    backendProcess = null;
  });

  for (let attempt = 0; attempt < 24; attempt += 1) {
    if (await checkBackend()) {
      return true;
    }
    await delay(500);
  }

  console.warn("[IRA] Backend did not become ready on port 8765.");
  return false;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1120,
    height: 760,
    minWidth: 880,
    minHeight: 620,
    title: "IRA",
    backgroundColor: "#0f1412",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      enableRemoteModule: false,
      sandbox: false
    }
  });

  if (isDev) {
    win.loadURL(devServerURL);
  } else {
    win.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(async () => {
  setupPermissions();
  await startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }

  if (process.platform !== "darwin") {
    app.quit();
  }
});
