import { useState, useRef, useEffect } from "react";

export default function InputBar({ onSend, loading }) {
    const [message, setMessage] = useState("");
    const textareaRef = useRef(null);

    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = "auto";
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
        }
    }, [message]);

    const handleSubmit = () => {
        const trimmed = message.trim();
        if (!trimmed || loading) return;
        onSend(trimmed);
        setMessage("");
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="shrink-0 px-6 py-4" style={{ borderTop: "1px solid var(--border)" }}>
            <div className="max-w-2xl mx-auto">
                <div
                    className="flex items-end gap-3 rounded-xl px-4 py-3"
                    style={{
                        background: "var(--bg-card)",
                        border: "1px solid var(--border)",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                    }}
                >
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask a question..."
                        disabled={loading}
                        rows={1}
                        className="flex-1 resize-none bg-transparent text-sm outline-none disabled:opacity-50"
                        style={{
                            color: "var(--text-primary)",
                            "::placeholder": { color: "var(--text-muted)" },
                        }}
                    />
                    <button
                        onClick={handleSubmit}
                        disabled={loading || !message.trim()}
                        className="shrink-0 p-2 rounded-lg transition-all disabled:opacity-30"
                        style={{
                            background: message.trim() ? "var(--accent)" : "transparent",
                            color: message.trim() ? "#FFFFFF" : "var(--text-muted)",
                        }}
                    >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                        </svg>
                    </button>
                </div>
                <p className="text-center mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                    Fetches live data from Monday.com on every query
                </p>
            </div>
        </div>
    );
}
