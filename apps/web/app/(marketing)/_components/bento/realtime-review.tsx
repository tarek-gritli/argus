"use client"

import type React from "react"

const RealtimeReview: React.FC = () => {
  return (
    <div
      style={{ width: "100%", height: "100%", position: "relative", background: "transparent" } as React.CSSProperties}
      role="img"
      aria-label="Real-time review showing split diff with agent annotations"
    >
      {/* Left Panel - Diff view */}
      <div
        style={{
          position: "absolute",
          top: "46px",
          left: "50%",
          transform: "translateX(-50%)",
          width: "350px",
          height: "221px",
          background: "linear-gradient(180deg, oklch(0.1 0 0 / 80%) 0%, transparent 100%)",
          backdropFilter: "blur(7.907px)",
          borderRadius: "9.488px",
          border: "1px solid oklch(1 0 0 / 10%)",
          overflow: "hidden",
          boxSizing: "border-box",
        }}
      >
        <div style={{ padding: "9.488px 9.492px", height: "100%", boxSizing: "border-box", position: "relative", overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ fontFamily: "'Geist Mono', monospace", fontSize: "10.279px", lineHeight: "15.814px", letterSpacing: "-0.3163px", color: "oklch(0.85 0 0)", width: "100%", position: "relative", margin: 0, flexGrow: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, color: "oklch(0.55 0.15 142)", display: "block" }}>{"+ parameterized_query(sql, params)"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, color: "oklch(0.55 0.18 27)", display: "block" }}>{"- cursor.execute(f\"SELECT * FROM {table}\""}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, display: "block" }}>{" "}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, color: "oklch(0.55 0.15 142)", display: "block" }}>{"+ if token := validate_jwt(request):"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, color: "oklch(0.55 0.18 27)", display: "block" }}>{"- if auth_token == secret_key:"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, display: "block" }}>{" "}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, display: "block" }}>{"  def process_request(data):"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, display: "block" }}>{"    validated = schema.load(data)"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400, display: "block" }}>{"    return handler(validated)"}</p>
          </div>
        </div>
      </div>

      {/* Right Panel - Agent badge */}
      <div
        style={{
          position: "absolute",
          top: "46px",
          left: "calc(50% + 87.499px)",
          transform: "translateX(-50%)",
          width: "175px",
          height: "221px",
          background: "linear-gradient(180deg, oklch(0.1 0 0 / 80%) 0%, transparent 100%)",
          backdropFilter: "blur(7.907px)",
          borderRadius: "9.488px",
          overflow: "hidden",
          boxSizing: "border-box",
        }}
      >
        <div style={{ padding: "9.488px 9.492px", height: "100%", boxSizing: "border-box", position: "relative", overflow: "hidden", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "oklch(0.12 0 0 / 80%)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "7.907px", background: "oklch(0.94 0 0)", color: "oklch(0.1 0 0)", border: "none", cursor: "pointer", fontWeight: 500, whiteSpace: "nowrap", padding: "6.326px 12.651px", borderRadius: "11.07px", fontSize: "12px", lineHeight: "18px" }}>
            Security
          </div>
        </div>
      </div>

      {/* Connection Line */}
      <div style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%, -50%)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative", width: "2px", height: "285.088px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width="2" height="285.088" viewBox="0 0 2 285.088" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ position: "absolute", inset: 0, display: "block", maxWidth: "none", width: "100%", height: "100%" }}>
            <defs>
              <linearGradient id="reviewConnectionGradient" x1="1" y1="0" x2="1" y2="285.088" gradientUnits="userSpaceOnUse">
                <stop stopColor="oklch(0.94 0 0)" stopOpacity="0" />
                <stop offset="0.5" stopColor="oklch(0.94 0 0)" />
                <stop offset="1" stopColor="oklch(0.94 0 0)" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d="M1 0V285.088" stroke="url(#reviewConnectionGradient)" strokeWidth="2" />
          </svg>
        </div>
      </div>
    </div>
  )
}

export default RealtimeReview
