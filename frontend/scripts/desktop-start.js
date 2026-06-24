const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const PORT = 5173;
const BACKEND_PORT = 8765;
const HOST = "127.0.0.1";
const DEV_URL = `http://${HOST}:${PORT}`;
const BACKEND_URL = `http://${HOST}:${BACKEND_PORT}/health`;

function checkServer(url) {
  return new Promise((resolve) => {
    http
      .get(url, (response) => {
        response.resume();
        resolve(response.statusCode >= 200 && response.statusCode < 500);
      })
      .on("error", () => resolve(false));
  });
}

function spawnBackend() {
  const nodeCmd = process.execPath;
  const child = spawn(nodeCmd, [path.join("scripts", "backend-keepalive.js")], {
    stdio: "inherit",
    windowsHide: true,
    shell: false,
  });

  child.on("exit", (code) => {
    if (code !== 0 && code !== null) {
      console.error(`IRA backend keeper stopped with code ${code}.`);
    }
  });

  return child;
}

function spawnVite() {
  const viteCmd = process.platform === "win32" ? path.join("node_modules", ".bin", "vite.cmd") : path.join("node_modules", ".bin", "vite");
  const child = spawn(viteCmd, ["--host", "0.0.0.0", "--port", String(PORT)], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  child.on("exit", (code) => {
    if (code !== 0) {
      process.exit(code);
    }
  });
  return child;
}

function spawnElectron() {
  const electronCmd = require("electron");
  const electronArgs = [".", ...process.argv.slice(2)];
  const electronEnv = { ...process.env };

  delete electronEnv.ELECTRON_RUN_AS_NODE;
  delete electronEnv.ELECTRON_NO_ATTACH_CONSOLE;

  const child = spawn(electronCmd, electronArgs, {
    env: electronEnv,
    stdio: "inherit",
    windowsHide: false,
    shell: false,
  });
  child.on("exit", (code) => {
    process.exit(code);
  });
  return child;
}

(async () => {
  const backendUp = await checkServer(BACKEND_URL);
  let backendProcess = null;

  if (!backendUp) {
    console.log("Starting IRA backend on port 8765...");
    backendProcess = spawnBackend();

    const startTime = Date.now();
    while (Date.now() - startTime < 12000) {
      const ready = await checkServer(BACKEND_URL);
      if (ready) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    if (!(await checkServer(BACKEND_URL))) {
      console.error("IRA backend did not start on port 8765.");
      process.exit(1);
    }
  } else {
    console.log("Reusing existing IRA backend on port 8765.");
  }

  const serverUp = await checkServer(DEV_URL);
  let viteProcess = null;

  if (!serverUp) {
    console.log("Starting Vite dev server on port 5173...");
    viteProcess = spawnVite();

    const startTime = Date.now();
    while (Date.now() - startTime < 20000) {
      const ready = await checkServer(DEV_URL);
      if (ready) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    if (!(await checkServer(DEV_URL))) {
      console.error("Vite dev server did not start on port 5173.");
      process.exit(1);
    }
  } else {
    console.log("Reusing existing Vite server on port 5173.");
  }

  spawnElectron();

  process.on("SIGINT", () => {
    if (backendProcess) {
      backendProcess.kill("SIGINT");
    }
    if (viteProcess) {
      viteProcess.kill("SIGINT");
    }
    process.exit();
  });
})();
