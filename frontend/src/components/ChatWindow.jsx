import { useRef, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

/* ── Rotating sample queries across categories ── */
const QUERY_SETS = [
    [
        "How is our pipeline looking?",
        "Total value of open work orders?",
        "Which deals are at risk?",
        "Mining vs Construction?",
    ],
    [
        "What's our pipeline health this quarter?",
        "Show me overdue work orders",
        "Top sectors by deal value?",
        "How many deals are in proposal stage?",
    ],
    [
        "Give me a revenue summary",
        "Which work orders are stalling?",
        "Break down deals by closure probability",
        "What's our average deal size?",
    ],
];

export default function ChatWindow({ messages, loading, onSuggestionClick }) {
    const bottomRef = useRef(null);
    const [querySetIndex, setQuerySetIndex] = useState(() =>
        Math.floor(Math.random() * QUERY_SETS.length)
    );

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Rotate queries every 8 seconds while on empty state
    useEffect(() => {
        if (messages.length > 0) return;
        const interval = setInterval(() => {
            setQuerySetIndex((prev) => (prev + 1) % QUERY_SETS.length);
        }, 8000);
        return () => clearInterval(interval);
    }, [messages.length]);

    const currentQueries = QUERY_SETS[querySetIndex];

    if (!messages || messages.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center max-w-lg">
                    <div className="mb-5">
                        <svg className="h-10 w-10 mx-auto" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5">
                            <rect x="3" y="12" width="4" height="9" rx="1" />
                            <rect x="10" y="6" width="4" height="15" rx="1" />
                            <rect x="17" y="3" width="4" height="18" rx="1" />
                        </svg>
                    </div>
                    <h2 className="text-lg font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                        What would you like to know?
                    </h2>
                    <p className="text-sm leading-relaxed mb-8" style={{ color: "var(--text-muted)" }}>
                        I can pull live data from your Monday.com boards and give you concise business insights.
                    </p>
                    <div className="flex flex-wrap gap-2 justify-center transition-all duration-500">
                        {currentQueries.map((q) => (
                            <button
                                key={q}
                                onClick={() => onSuggestionClick(q)}
                                className="text-xs px-3 py-2 rounded-lg transition-all cursor-pointer animate-fadeUp"
                                style={{
                                    background: "var(--bg-secondary)",
                                    color: "var(--text-secondary)",
                                    border: "1px solid var(--border)",
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = "var(--accent)";
                                    e.currentTarget.style.color = "var(--accent)";
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = "var(--border)";
                                    e.currentTarget.style.color = "var(--text-secondary)";
                                }}
                            >
                                {q}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-6 py-6 space-y-6">
                {messages.map((msg, index) => (
                    <div key={index} className="animate-fadeUp">
                        {msg.role === "user" ? (
                            <div className="flex justify-end">
                                <p
                                    className="text-sm px-4 py-2.5 rounded-2xl rounded-br-md max-w-[75%]"
                                    style={{
                                        background: "var(--accent-user)",
                                        color: "#FFFFFF",
                                    }}
                                >
                                    {msg.content}
                                </p>
                            </div>
                        ) : (
                            <div>
                                {/* Markdown-rendered response with teal accent border */}
                                <div
                                    className="pl-4 text-sm leading-relaxed prose-compact"
                                    style={{
                                        borderLeft: "2px solid var(--accent)",
                                        color: "var(--text-primary)",
                                    }}
                                >
                                    <ReactMarkdown
                                        components={{
                                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                            ul: ({ children }) => <ul className="mb-2 pl-4 list-disc">{children}</ul>,
                                            ol: ({ children }) => <ol className="mb-2 pl-4 list-decimal">{children}</ol>,
                                            li: ({ children }) => <li className="mb-1">{children}</li>,
                                            strong: ({ children }) => (
                                                <strong className="font-semibold" style={{ color: "var(--text-primary)" }}>
                                                    {children}
                                                </strong>
                                            ),
                                            h1: ({ children }) => <h3 className="font-semibold text-base mb-2">{children}</h3>,
                                            h2: ({ children }) => <h3 className="font-semibold text-base mb-2">{children}</h3>,
                                            h3: ({ children }) => <h4 className="font-semibold text-sm mb-1">{children}</h4>,
                                            table: ({ children }) => (
                                                <div className="overflow-x-auto my-2">
                                                    <table className="text-xs w-full" style={{ borderCollapse: "collapse" }}>
                                                        {children}
                                                    </table>
                                                </div>
                                            ),
                                            th: ({ children }) => (
                                                <th className="text-left px-2 py-1 font-medium" style={{ borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                                                    {children}
                                                </th>
                                            ),
                                            td: ({ children }) => (
                                                <td className="px-2 py-1" style={{ borderBottom: "1px solid var(--border)" }}>
                                                    {children}
                                                </td>
                                            ),
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>

                                {/* Response time badge */}
                                {msg.responseTime && (
                                    <div className="pl-4 mt-1.5">
                                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                                            {msg.responseTime}s
                                        </span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                {loading && (
                    <div className="animate-fadeUp">
                        <div
                            className="pl-4 flex items-center gap-2"
                            style={{ borderLeft: "2px solid var(--accent)" }}
                        >
                            <div className="flex gap-1">
                                <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "var(--accent)", animationDelay: "0ms" }} />
                                <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "var(--accent)", animationDelay: "200ms" }} />
                                <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "var(--accent)", animationDelay: "400ms" }} />
                            </div>
                            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                                Analyzing...
                            </span>
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    );
}
