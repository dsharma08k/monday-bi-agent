import { useState, useEffect } from "react";
import ChatWindow from "./components/ChatWindow";
import InputBar from "./components/InputBar";
import ActionTrace from "./components/ActionTrace";
import DataQualityReport from "./components/DataQualityReport";
import { sendQuery } from "./api/monday";

/* Logo component */
function Logo() {
  return (
    <img
      src="/logo.png"
      alt="Monday BI Agent"
      className="h-8 w-8 rounded-lg"
    />
  );
}

function App() {
  const [messages, setMessages] = useState([]);
  const [actionTrace, setActionTrace] = useState([]);
  const [dataQualityReport, setDataQualityReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem("theme") === "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const handleSend = async (message) => {
    const userMessage = { role: "user", content: message };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setLoading(true);
    setActionTrace(["Sending query to agent..."]);
    setTraceOpen(true);

    const startTime = Date.now();

    try {
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await sendQuery(message, history);
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

      const assistantMessage = {
        role: "assistant",
        content: response.answer,
        responseTime: elapsed,
      };
      setMessages([...updatedMessages, assistantMessage]);
      setActionTrace(response.action_trace || []);
      setDataQualityReport(response.data_quality_report || null);
    } catch (error) {
      console.error("Query error:", error);
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      const errorMessage = {
        role: "assistant",
        content:
          error.response?.data?.detail ||
          "Sorry, something went wrong. Please check that the backend is running and try again.",
        responseTime: elapsed,
      };
      setMessages([...updatedMessages, errorMessage]);
      setActionTrace((prev) => [...prev, `❌ Error: ${error.message}`]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col" style={{ background: "var(--bg-primary)" }}>
      {/* Header */}
      <header
        className="shrink-0 flex items-center justify-between px-6 py-3"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-3">
          <Logo />
          <div>
            <h1 className="text-sm font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Monday BI Agent
            </h1>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Live intelligence from your boards
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Dark mode toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-full cursor-pointer"
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
              e.currentTarget.style.color = "var(--accent)";
              e.currentTarget.style.transform = "scale(1.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.color = "var(--text-secondary)";
              e.currentTarget.style.transform = "scale(1)";
            }}
            title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {darkMode ? (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>

          {/* Trace toggle */}
          <button
            onClick={() => setTraceOpen(!traceOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
            style={{
              background: traceOpen ? "var(--accent-light)" : "var(--bg-secondary)",
              color: traceOpen ? "var(--accent)" : "var(--text-secondary)",
              border: `1px solid ${traceOpen ? "var(--accent)" : "var(--border)"}`,
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => {
              if (!traceOpen) {
                e.currentTarget.style.borderColor = "var(--accent)";
                e.currentTarget.style.color = "var(--accent)";
              }
              e.currentTarget.style.transform = "scale(1.03)";
            }}
            onMouseLeave={(e) => {
              if (!traceOpen) {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: traceOpen ? "var(--accent)" : "var(--text-muted)" }}
            />
            Trace
            {actionTrace.length > 0 && (
              <span className="ml-0.5" style={{ opacity: 0.7 }}>
                ({actionTrace.length})
              </span>
            )}
          </button>
        </div>
      </header>

      {/* Main */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <ChatWindow messages={messages} loading={loading} onSuggestionClick={handleSend} />
          <InputBar onSend={handleSend} loading={loading} />
        </div>

        {/* Sidebar — softened with padding and inner rounded card */}
        <div
          className="shrink-0 overflow-hidden transition-all duration-300 ease-in-out"
          style={{
            width: traceOpen ? "340px" : "0px",
            borderLeft: traceOpen ? "1px solid var(--border)" : "none",
          }}
        >
          <div className="w-[340px] h-full p-3 flex flex-col gap-3" style={{ background: "var(--bg-primary)" }}>
            {/* Trace card */}
            <div
              className="flex-1 overflow-hidden rounded-xl"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
              }}
            >
              <ActionTrace steps={actionTrace} />
            </div>

            {/* Quality card */}
            <div
              className="shrink-0 rounded-xl overflow-hidden"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
              }}
            >
              <DataQualityReport report={dataQualityReport} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
