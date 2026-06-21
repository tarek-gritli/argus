import type React from "react"

const ParallelAgents: React.FC = () => {
  const CheckmarkIcon = () => (
    <svg width="13.885" height="13.885" viewBox="0 0 14 14" fill="none" style={{ width: "13.885px", height: "13.885px" }}>
      <path d="M3.85156 7.875L6.47656 10.5L10.8516 3.5" stroke="oklch(0.85 0 0)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" opacity="0.8" />
    </svg>
  )

  const RefreshIcon = () => (
    <svg width="13.885" height="13.885" viewBox="0 0 14 14" fill="none" style={{ width: "13.885px", height: "13.885px" }}>
      <path d="M1.75 7C1.75 4.1005 4.1005 1.75 7 1.75C9.8995 1.75 12.25 4.1005 12.25 7C12.25 9.8995 9.8995 12.25 7 12.25" stroke="oklch(0.85 0 0)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" opacity="0.8" />
      <path d="M4.375 10.5L1.75 12.25L3.5 9.625" stroke="oklch(0.85 0 0)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" opacity="0.8" />
    </svg>
  )

  const SparklesIcon = () => (
    <svg width="13.885" height="13.885" viewBox="0 0 14 14" fill="none" style={{ width: "13.885px", height: "13.885px" }}>
      <path d="M7 1.75L8.225 5.775L12.25 7L8.225 8.225L7 12.25L5.775 8.225L1.75 7L5.775 5.775L7 1.75Z" stroke="oklch(0.85 0 0)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" opacity="0.8" />
    </svg>
  )

  const agents = [
    { icon: <CheckmarkIcon />, title: "Security scan complete", tokens: "18k tokens", model: "claude-sonnet-4-6", branch: "argus/pr-2847" },
    { icon: <RefreshIcon />, title: "Quality analysis running", tokens: "12k tokens", model: "claude-sonnet-4-6", branch: "argus/pr-2847" },
    { icon: <SparklesIcon />, title: "Fix engine generating patch", tokens: "30k tokens", model: "claude-sonnet-4-6", branch: "argus/pr-2847" },
  ]

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        background: "linear-gradient(180deg, oklch(0.14 0 0 / 40%) 0%, transparent 100%)",
        backdropFilter: "blur(8.372px)",
        borderRadius: "10.047px",
        boxSizing: "border-box",
        margin: "0 auto",
      } as React.CSSProperties}
      role="img"
      aria-label="Parallel agents running security, quality, and fix engine simultaneously"
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "flex-start",
          gap: "16px",
          padding: "20px",
          height: "100%",
          width: "calc(100% - 48px)",
          background: "linear-gradient(180deg, oklch(0.94 0 0 / 5%) 0%, transparent 100%)",
          backdropFilter: "blur(16px)",
          borderRadius: "9.628px",
          border: "0.802px solid oklch(1 0 0 / 10%)",
          overflow: "hidden",
          boxSizing: "border-box",
          margin: "24px 24px 0 24px",
        }}
      >
        {agents.map((agent, index) => (
          <div
            key={index}
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "flex-start",
              gap: "8.658px",
              padding: "6.494px 8.658px",
              background: "linear-gradient(180deg, oklch(0.14 0 0 / 20%) 0%, transparent 100%)",
              backdropFilter: "blur(19.481px)",
              borderRadius: "8.658px",
              border: "0.541px solid oklch(1 0 0 / 10%)",
              width: "100%",
              maxWidth: "320px",
              flexShrink: 0,
              position: "relative",
              overflow: "hidden",
              boxSizing: "border-box",
            }}
          >
            <div style={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "flex-start", gap: "8.658px", padding: "3.247px 0 0 0", flexShrink: 0 }}>
              <div style={{ width: "17.316px", height: "17.316px", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", flexShrink: 0 }}>
                {agent.icon}
              </div>
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                justifyContent: "center",
                gap: "2.164px",
                padding: "0",
                flexShrink: 0,
                ...(index === 1 ? { flexBasis: 0, flexGrow: 1, minHeight: "1px", minWidth: "1px" } : {}),
              }}
            >
              <div style={{ fontFamily: "'Inter', sans-serif", fontWeight: 400, fontSize: "10.823px", lineHeight: "17.316px", color: "oklch(0.85 0 0)", whiteSpace: "pre", flexShrink: 0 }}>
                {agent.title}
              </div>
              <div
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 400,
                  fontSize: "10.823px",
                  lineHeight: "17.316px",
                  color: "oklch(0.5 0 0)",
                  whiteSpace: index === 1 ? "nowrap" : "pre",
                  overflow: index === 1 ? "hidden" : "visible",
                  textOverflow: index === 1 ? "ellipsis" : "clip",
                  width: index === 1 ? "100%" : "auto",
                  minWidth: index === 1 ? "100%" : "auto",
                  flexShrink: 0,
                }}
              >
                {`${agent.tokens} • ${agent.model} • ${agent.branch}`}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ParallelAgents
