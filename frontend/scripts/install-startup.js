const fs = require("fs");
const os = require("os");
const path = require("path");

if (process.platform !== "win32") {
  console.error("IRA startup install currently supports Windows only.");
  process.exit(1);
}

const startupDir = path.join(
  process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming"),
  "Microsoft",
  "Windows",
  "Start Menu",
  "Programs",
  "Startup"
);
const frontendDir = path.resolve(__dirname, "..");
const npmCmd = path.join(process.env.ProgramFiles || "C:\\Program Files", "nodejs", "npm.cmd");
const startupFile = path.join(startupDir, "IRA.cmd");

const command = [
  "@echo off",
  `cd /d "${frontendDir}"`,
  `start "" /min "${npmCmd}" run desktop -- --start-minimized`,
  ""
].join("\r\n");

fs.mkdirSync(startupDir, { recursive: true });
fs.writeFileSync(startupFile, command, "utf-8");

console.log(`IRA will start with Windows: ${startupFile}`);
