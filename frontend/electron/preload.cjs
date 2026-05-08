const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("iraDesktop", {
  platform: process.platform
});
