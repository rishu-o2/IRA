const { app, BrowserWindow, ipcMain, session } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const readline = require("node:readline");

app.commandLine.appendSwitch("enable-experimental-web-platform-features");
app.commandLine.appendSwitch("enable-features", "WebSpeechAPI");
app.commandLine.appendSwitch("disable-gpu-shader-disk-cache");
app.commandLine.appendSwitch("disable-gpu-program-cache");

const shouldLoadFile = app.isPackaged || process.argv.includes("--load-file") || process.env.IRA_LOAD_FILE === "1";
const startMinimized = process.argv.includes("--start-minimized") || process.env.IRA_START_MINIMIZED === "1";
let mainWindow = null;

// Get the local dev server URL
const getDevServerURL = () => {
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl && devUrl.trim()) return devUrl.trim();
  
  // Always use localhost for dev - it's accessible from the same machine
  return "http://localhost:5173";
};

const devServerURL = getDevServerURL();
let backendProcess = null;
let speechProcess = null;
let speechRestartTimer = null;

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

function installWindowsStartupShortcut() {
  if (process.platform !== "win32") {
    return;
  }

  try {
    const startupDir = path.join(app.getPath("appData"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup");
    const frontendDir = path.resolve(__dirname, "..");
    const nodePath = path.join(process.env.ProgramFiles || "C:\\Program Files", "nodejs", "npm.cmd");
    const startupFile = path.join(startupDir, "IRA.cmd");
    let command = "";

    if (app.isPackaged) {
      const exePath = process.execPath;
      command = [
        "@echo off",
        `start "" /min "${exePath}"`,
        ""
      ].join("\r\n");
    } else {
      command = [
        "@echo off",
        `cd /d "${frontendDir}"`,
        `start "" /min "${nodePath}" run desktop -- --start-minimized`,
        ""
      ].join("\r\n");
    }

    fs.mkdirSync(startupDir, { recursive: true });
    fs.writeFileSync(startupFile, command, "utf-8");
    console.log(`[IRA] Installed startup shortcut: ${startupFile}`);
  } catch (error) {
    console.warn("[IRA] Failed to install startup shortcut:", error);
  }
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

function sendSpeechEvent(event) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("ira:speech-event", event);
  }
}

function startNativeSpeech() {
  if (process.platform !== "win32" || speechProcess) {
    return;
  }

  const scriptPath = path.resolve(__dirname, "..", "scripts", "windows-speech-listener.ps1");
  const powershell = path.join(process.env.SystemRoot || "C:\\Windows", "System32", "WindowsPowerShell", "v1.0", "powershell.exe");

  speechProcess = spawn(
    powershell,
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath],
    {
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"]
    }
  );

  sendSpeechEvent({ type: "status", status: "NATIVE VOICE STARTING" });

  const speechLines = readline.createInterface({ input: speechProcess.stdout });
  speechLines.on("line", (line) => {
    try {
      sendSpeechEvent(JSON.parse(line));
    } catch {
      sendSpeechEvent({ type: "status", status: line.trim() || "NATIVE LISTENING" });
    }
  });

  speechProcess.stderr.on("data", (chunk) => {
    const message = chunk.toString().trim();
    if (message) {
      sendSpeechEvent({ type: "error", error: message });
    }
  });

  speechProcess.on("error", (error) => {
    sendSpeechEvent({ type: "error", error: error.message });
    speechProcess = null;
  });

  speechProcess.on("exit", () => {
    speechProcess = null;
    sendSpeechEvent({ type: "status", status: "NATIVE VOICE RESTARTING" });

    if (!app.isQuitting) {
      speechRestartTimer = setTimeout(startNativeSpeech, 2000);
    }
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1120,
    height: 760,
    minWidth: 880,
    minHeight: 620,
    show: !startMinimized,
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

  mainWindow.on("close", (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  if (shouldLoadFile) {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  } else {
    mainWindow.loadURL(devServerURL);
  }

  mainWindow.once("ready-to-show", () => {
    if (startMinimized) {
      mainWindow.hide();
      return;
    }

    mainWindow.show();
    mainWindow.focus();
  });
}

function showMainWindow() {
  if (!mainWindow) {
    createWindow();
    return;
  }

  mainWindow.show();
  mainWindow.focus();
}

const singleInstanceLock = app.requestSingleInstanceLock();

if (!singleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    showMainWindow();
  });
}

app.whenReady().then(async () => {
  setupPermissions();
  ipcMain.handle("ira:show-window", () => {
    showMainWindow();
  });
  ipcMain.handle("ira:native-speech-supported", () => process.platform === "win32");
  installWindowsStartupShortcut();
  app.setLoginItemSettings({
    openAtLogin: true,
    args: ["--start-minimized"]
  });
  await startBackend();
  createWindow();
  startNativeSpeech();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else {
      showMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform === "darwin") {
    return;
  }
});

app.on("before-quit", () => {
  app.isQuitting = true;

  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }

  if (speechRestartTimer) {
    clearTimeout(speechRestartTimer);
    speechRestartTimer = null;
  }

  if (speechProcess) {
    speechProcess.kill();
    speechProcess = null;
  }
});
