const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("iraDesktop", {
  platform: process.platform,
  nativeSpeechSupported: () => ipcRenderer.invoke("ira:native-speech-supported"),
  onSpeechEvent: (callback) => {
    const listener = (_event, speechEvent) => callback(speechEvent);
    ipcRenderer.on("ira:speech-event", listener);
    return () => ipcRenderer.removeListener("ira:speech-event", listener);
  },
  showWindow: () => ipcRenderer.invoke("ira:show-window")
});
