import type React from "react"
import { Search } from "lucide-react"

const ContextSearch: React.FC = () => {
  const findings = [
    { name: "SQL Injection risk", file: "api/routes/users.py", severity: "critical", installed: true },
    { name: "Hardcoded secret", file: "config/settings.py", severity: "high", installed: true },
    { name: "Missing test coverage", file: "services/auth.py", severity: "medium" },
    { name: "Cyclomatic complexity", file: "utils/parser.py", severity: "low" },
    { name: "Undocumented public API", file: "api/reviews.py", severity: "info" },
    { name: "Dead code detected", file: "legacy/helpers.py", severity: "low" },
  ]

  return (
    <div className="w-full h-full flex items-center justify-center p-4 relative" role="img" aria-label="Semantic context search showing findings across the codebase">
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, calc(-50% + 24px))",
          width: "345px",
          height: "277px",
          background: "linear-gradient(180deg, oklch(0.1 0 0) 0%, transparent 100%)",
          backdropFilter: "blur(16px)",
          borderRadius: "9.628px",
          border: "0.802px solid oklch(1 0 0 / 10%)",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12.837px", padding: "8.826px 12.837px", borderBottom: "0.802px solid oklch(1 0 0 / 8%)", width: "100%", boxSizing: "border-box" }}>
            <div style={{ width: "14.442px", height: "14.442px", position: "relative", flexShrink: 0 }}>
              <Search className="w-full h-full" style={{ color: "oklch(0.5 0 0)" }} />
            </div>
            <span style={{ fontFamily: "'Geist', sans-serif", fontSize: "12.837px", lineHeight: "19.256px", color: "oklch(0.5 0 0)", fontWeight: 400, whiteSpace: "nowrap" }}>
              Search findings...
            </span>
          </div>
          {findings.map((finding, index) => (
            <div
              key={finding.name}
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8.826px 12.837px", borderBottom: index < findings.length - 1 ? "0.479px solid oklch(1 0 0 / 6%)" : "none", width: "100%", boxSizing: "border-box" }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <span style={{ fontFamily: "'Geist', sans-serif", fontSize: "12.837px", lineHeight: "19.256px", color: "oklch(0.85 0 0)", fontWeight: 400, whiteSpace: "nowrap" }}>
                  {finding.name}
                </span>
                <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: "10px", lineHeight: "14px", color: "oklch(0.5 0 0)", whiteSpace: "nowrap" }}>
                  {finding.file}
                </span>
              </div>
              {finding.installed && (
                <div style={{ background: "oklch(0.94 0 0 / 8%)", padding: "1.318px 5.272px", borderRadius: "3.295px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <span style={{ fontFamily: "'Geist', sans-serif", fontSize: "9.583px", lineHeight: "15.333px", color: "oklch(0.85 0 0)", fontWeight: 500, whiteSpace: "nowrap" }}>
                    {finding.severity}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ContextSearch
