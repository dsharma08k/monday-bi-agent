export default function ActionTrace({ steps }) {
    return (
        <div className="flex-1 overflow-y-auto p-5">
            <h3 className="text-xs font-semibold uppercase tracking-widest mb-4"
                style={{ color: "var(--text-muted)", letterSpacing: "0.1em" }}>
                Agent Trace
            </h3>

            {(!steps || steps.length === 0) ? (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Steps will appear here as the agent works...
                </p>
            ) : (
                <div className="space-y-0">
                    {steps.map((step, index) => {
                        const isLast = index === steps.length - 1;
                        const isSuccess = step.startsWith("✅");
                        const isError = step.startsWith("❌");

                        let dotColor = "var(--accent)";
                        if (isSuccess) dotColor = "#22C55E";
                        if (isError) dotColor = "#EF4444";

                        return (
                            <div key={index} className="flex items-start gap-3 animate-fadeUp">
                                {/* Timeline line + dot */}
                                <div className="flex flex-col items-center shrink-0">
                                    <div
                                        className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                                        style={{ background: dotColor }}
                                    />
                                    {!isLast && (
                                        <div className="w-px flex-1 min-h-5" style={{ background: "var(--border)" }} />
                                    )}
                                </div>

                                {/* Step text */}
                                <p className="text-xs leading-relaxed pb-3" style={{ color: "var(--text-secondary)" }}>
                                    {step}
                                </p>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
