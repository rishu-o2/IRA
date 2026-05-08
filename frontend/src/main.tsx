import React, { FormEvent, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Calculator,
  Cpu,
  Database,
  Eye,
  FolderOpen,
  Globe2,
  Mic,
  Music2,
  Radio,
  Send,
  ShieldCheck,
  Sparkles,
  TerminalSquare
} from "lucide-react";
import "./styles.css";

type Message = {
  id: number;
  sender: "user" | "ira";
  text: string;
};

type QuickCommand = {
  label: string;
  command: string;
  icon: React.ComponentType<{ size?: number }>;
};

const quickCommands: QuickCommand[] = [
  { label: "Notepad", command: "open notepad", icon: TerminalSquare },
  { label: "Calculator", command: "open calculator", icon: Calculator },
  { label: "YouTube", command: "open website youtube.com", icon: Globe2 },
  { label: "Downloads", command: "open folder C:\\Users\\hp\\Downloads", icon: FolderOpen },
  { label: "Music", command: "play relaxing music", icon: Music2 }
];

const capabilities = [
  { name: "DESKTOP COMMANDS", level: 72 },
  { name: "FILE SYSTEM ACCESS", level: 61 },
  { name: "WEB NAVIGATION", level: 78 },
  { name: "MEDIA CONTROL", level: 54 },
  { name: "VOICE MODULE", level: 32 }
];

const telemetry = [
  { label: "CPU", value: "21", unit: "%", tone: "cyan" },
  { label: "VOICE", value: "0.4", unit: "db", tone: "blue" },
  { label: "TASKS", value: "5", unit: "", tone: "cyan" },
  { label: "PING", value: "2.40", unit: "ms", tone: "blue" },
  { label: "MEM", value: "38", unit: "%", tone: "cyan" },
  { label: "SCAN", value: "13", unit: "fps", tone: "blue" }
];

const diagnostics = [
  ["Kernel", "standby"],
  ["Vision", "queued"],
  ["Memory", "local"],
  ["Network", "online"],
  ["Bridge", "pending"],
  ["Security", "armed"]
];

const eventLog = [
  "00:01 core boot sequence accepted",
  "00:04 local command parser mounted",
  "00:07 desktop action module waiting",
  "00:11 user interface synchronized",
  "00:15 execution bridge scheduled"
];

const systemNodes = [
  { label: "VISION", icon: Eye },
  { label: "MEMORY", icon: Database },
  { label: "VOICE", icon: Radio },
  { label: "TOOLS", icon: Sparkles }
];

const initialMessages: Message[] = [
  {
    id: 1,
    sender: "ira",
    text: "IRA interface online. Start the backend server to execute desktop commands from this console."
  }
];

async function sendCommandToBackend(command: string): Promise<string> {
  const response = await fetch("http://127.0.0.1:8765/command", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ message: command })
  });

  if (!response.ok) {
    throw new Error("Backend request failed");
  }

  const payload = (await response.json()) as { text?: string };
  return payload.text ?? "Command completed.";
}

function App() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);

  const lastCommand = useMemo(() => {
    return [...messages].reverse().find((message) => message.sender === "user")?.text ?? "No command sent yet";
  }, [messages]);

  async function submitCommand(commandText: string) {
    const command = commandText.trim();

    if (!command || isExecuting) {
      return;
    }

    const userMessageId = Date.now();
    const iraMessageId = userMessageId + 1;

    setMessages((current) => [
      ...current,
      { id: userMessageId, sender: "user", text: command },
      { id: iraMessageId, sender: "ira", text: "Executing command through IRA backend..." }
    ]);
    setInput("");
    setIsExecuting(true);

    try {
      const backendResponse = await sendCommandToBackend(command);

      setMessages((current) =>
        current.map((message) => (message.id === iraMessageId ? { ...message, text: backendResponse } : message))
      );
    } catch {
      setMessages((current) =>
        current.map((message) =>
          message.id === iraMessageId
            ? {
                ...message,
                text: "Backend is not connected. Start it with: cd backend && python -m ira.server"
              }
            : message
        )
      );
    } finally {
      setIsExecuting(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitCommand(input);
  }

  return (
    <main className="app-shell">
      <div className="scanline" aria-hidden="true" />
      <section className="workspace">
        <header className="topbar">
          <div className="identity">
            <div>
              <h1>IRA</h1>
              <p>INTELLIGENT RESPONSIVE ASSISTANT</p>
            </div>
          </div>
          <div className="system-state" aria-label="System state">
            <span className="status-dot" />
            SYSTEM ONLINE
          </div>
        </header>

        <section className="telemetry-row" aria-label="System telemetry">
          {telemetry.map((item) => (
            <article key={item.label} className="telemetry-dial">
              <div className="dial-ring">
                <strong>{item.value}</strong>
                <span>{item.unit}</span>
              </div>
              <p>{item.label}</p>
            </article>
          ))}
        </section>

        <section className="command-center" aria-label="IRA command center">
          <aside className="side-panel">
            <div className="panel-section">
              <h2>COMMAND SHORTCUTS</h2>
              <div className="quick-grid">
                {quickCommands.map((item) => {
                  const Icon = item.icon;

                  return (
                    <button key={item.command} type="button" onClick={() => submitCommand(item.command)} title={item.command}>
                      <Icon size={18} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="panel-section">
              <h2>ACTIVE MODULES</h2>
              <ul className="capability-list">
                {capabilities.map((capability) => (
                  <li key={capability.name}>
                    <span>{capability.name}</span>
                    <meter min="0" max="100" value={capability.level}>
                      {capability.level}%
                    </meter>
                  </li>
                ))}
              </ul>
            </div>

            <div className="panel-section">
              <h2>SYSTEM NODES</h2>
              <div className="node-grid">
                {systemNodes.map((node) => {
                  const Icon = node.icon;

                  return (
                    <div key={node.label}>
                      <Icon size={17} />
                      <span>{node.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="panel-section compact">
              <h2>LAST COMMAND</h2>
              <p>{lastCommand}</p>
            </div>
          </aside>

          <section className="core-stage" aria-label="IRA core">
            <div className="core-grid" aria-hidden="true" />
            <div className="hud-corners" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className="core-orbit">
              <div className="core-ring halo" />
              <div className="core-ring outer" />
              <div className="core-ring data-a" />
              <div className="core-ring data-b" />
              <div className="core-ring mid" />
              <div className="core-ring inner" />
              <div className="core-eye">
                <Cpu size={38} />
              </div>
            </div>

            <div className="core-caption">
              <span>NEURAL INTERFACE</span>
              <strong>IRA CORE</strong>
              <p>Awaiting execution bridge</p>
            </div>

            <div className="signal-strip" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>

            <div className="waveform" aria-label="Voice waveform">
              {Array.from({ length: 28 }, (_, index) => (
                <span key={index} style={{ "--i": index } as React.CSSProperties} />
              ))}
            </div>
          </section>

          <section className="right-stack">
            <aside className="diagnostic-panel">
              <div className="panel-header">
                <h2>DIAGNOSTICS</h2>
                <ShieldCheck size={17} />
              </div>
              <div className="diagnostic-list">
                {diagnostics.map(([label, value]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
            </aside>

            <aside className="event-panel">
              <div className="panel-header">
                <h2>MISSION LOG</h2>
                <Activity size={17} />
              </div>
              <ol>
                {eventLog.map((event) => (
                  <li key={event}>{event}</li>
                ))}
              </ol>
            </aside>

            <section className="chat-panel">
              <div className="chat-header">
                <div>
                  <h2>ASSISTANT CONSOLE</h2>
                  <p>Local frontend logic active</p>
                </div>
                <div className="desktop-chip">
                  <Radio size={16} />
                  DESKTOP
                </div>
              </div>

              <div className="message-list" aria-live="polite">
                {messages.map((message) => (
                  <article key={message.id} className={`message ${message.sender}`}>
                    <span>{message.sender === "ira" ? "IRA" : "You"}</span>
                    <p>{message.text}</p>
                  </article>
                ))}
              </div>

              <form className="composer" onSubmit={handleSubmit}>
                <button type="button" className="icon-button" title="Voice input planned" aria-label="Voice input planned">
                  <Mic size={20} />
                </button>
                <input
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder={isExecuting ? "EXECUTING..." : "ENTER COMMAND"}
                  aria-label="Command"
                  disabled={isExecuting}
                />
                <button type="submit" className="send-button" aria-label="Send command" disabled={isExecuting}>
                  <Send size={19} />
                </button>
              </form>
            </section>
          </section>
        </section>
      </section>

      <footer className="footer-strip">
        <span>
          <Activity size={15} />
          PROTOTYPE PHASE
        </span>
        <span>BACKEND EXECUTION BRIDGE COMING NEXT</span>
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
