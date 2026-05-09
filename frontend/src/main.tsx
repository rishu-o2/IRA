import React from "react";
import { createRoot } from "react-dom/client";
import { IraAvatar3D } from "./IraAvatar3D";
import "./styles.css";

function App() {
  return (
    <main className="app-shell" aria-label="IRA hologram">
      <IraAvatar3D />
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
