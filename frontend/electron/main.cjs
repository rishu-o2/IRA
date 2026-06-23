const { app, BrowserWindow, session } = require("electron");
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

app.whenReady().then(() => {
  setupPermissions();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
