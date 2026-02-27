import { useState } from "react";

export default function DataQualityReport({ report }) {
    const [expanded, setExpanded] = useState(false);

    if (!report || !report.summary) {
        return null;
    }

    const totalIssues =
        (report.missing_values || 0) +
        (report.unparseable_dates || 0) +
        (report.unparseable_numbers || 0);

    return (
        <div className="shrink-0 p-5">
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center justify-between"
            >
                <h3 className="text-xs font-semibold uppercase tracking-widest"
                    style={{ color: "var(--text-muted)", letterSpacing: "0.1em" }}>
                    Data Quality
                </h3>
                <svg
                    className={`h-3.5 w-3.5 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                    style={{ color: "var(--text-muted)" }}
                >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {/* Summary */}
            <p className="text-xs mt-2" style={{
                color: totalIssues === 0 ? "#22C55E" : "#F59E0B"
            }}>
                {totalIssues === 0
                    ? "No issues found"
                    : `${totalIssues} issues · ${report.total_items || 0} items`}
            </p>

            {/* Details */}
            {expanded && (
                <div className="mt-3 space-y-2 animate-fadeUp">
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { label: "Items", value: report.total_items || 0 },
                            { label: "Missing", value: report.missing_values || 0, warn: true },
                            { label: "Bad Dates", value: report.unparseable_dates || 0 },
                            { label: "Bad Numbers", value: report.unparseable_numbers || 0 },
                        ].map((item) => (
                            <div key={item.label} className="rounded-lg px-3 py-2"
                                style={{ background: "var(--bg-primary)" }}>
                                <div className="text-xs" style={{ color: "var(--text-muted)" }}>{item.label}</div>
                                <div className="text-sm font-medium mt-0.5"
                                    style={{ color: item.warn && item.value > 0 ? "#F59E0B" : "var(--text-primary)" }}>
                                    {item.value}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
