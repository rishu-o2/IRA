const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const PORT = 5173;
const HOST = "127.0.0.1";
const DEV_URL = `http://${HOST}:${PORT}`;

function checkServer(url) {
  return new Promise((resolve) => {
    http
      .get(url, () => resolve(true))
      .on("error", () => resolve(false));
  });
}

function spawnVite() {
  const viteCmd = process.platform === "win32" ? path.join("node_modules", ".bin", "vite.cmd") : path.join("node_modules", ".bin", "vite");
  const child = spawn(viteCmd, ["--host", "0.0.0.0", "--port", String(PORT)], {
    stdio: "inherit",
    shell: false,
  });
  child.on("exit", (code) => {
    if (code !== 0) {
      process.exit(code);
    }
  });
  return child;
}

function spawnElectron() {
  const electronCmd = process.platform === "win32" ? path.join("node_modules", ".bin", "electron.cmd") : path.join("node_modules", ".bin", "electron");
  const child = spawn(electronCmd, ["."], {
    stdio: "inherit",
    shell: false,
  });
  child.on("exit", (code) => {
    process.exit(code);
  });
  return child;
}

(async () => {
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
    if (viteProcess) {
      viteProcess.kill("SIGINT");
    }
    process.exit();
  });
})();
