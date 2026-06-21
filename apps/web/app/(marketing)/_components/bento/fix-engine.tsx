import type React from "react"

const FixEngine: React.FC = () => {
  const logLines = [
    "[14:22:31.021] Running security scan on 47 changed files...",
    "[14:22:31.184] SQL injection detected in api/routes/users.py:142",
    "[14:22:31.209] Fix engine generating patch...",
    "[14:22:32.441] Patch validated — Python 3.12, ruff clean",
    "[14:22:32.560] Confidence score: 0.97 (critical severity)",
    '[14:22:32.891] Running "argus post-review"',
    "[14:22:33.102] Argus CLI 1.4.2",
    "[14:22:33.320] Posting 12 findings as GitHub review...",
    "[14:22:33.801] 3 inline fix suggestions attached",
    "[14:22:34.210] Review posted to PR #2847",
    "[14:22:34.450] Quality agent: 2 complexity warnings",
    "[14:22:34.612] Testing agent: 4 coverage gaps found",
    "[14:22:34.891] Documentation agent: 1 undocumented API",
    "[14:22:35.100] All agents complete in 4.1s",
    "[14:22:35.201] Review complete — 12 findings, 3 auto-fixes",
  ]

  return (
    <div className="w-full h-full flex items-center justify-center p-4 relative" role="img" aria-label="Fix engine terminal output showing automated code fixes">
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "340px",
          height: "239px",
          background: "linear-gradient(180deg, oklch(0.1 0 0) 0%, transparent 100%)",
          backdropFilter: "blur(7.907px)",
          borderRadius: "10px",
          overflow: "hidden",
        }}
      >
        <div style={{ position: "absolute", inset: "2px", borderRadius: "8px", background: "oklch(1 0 0 / 4%)" }} />
        <div
          style={{
            position: "relative",
            padding: "8px",
            height: "100%",
            overflow: "hidden",
            fontFamily: "'Geist Mono', 'SF Mono', Monaco, Consolas, 'Liberation Mono', monospace",
            fontSize: "10px",
            lineHeight: "16px",
            color: "oklch(0.85 0 0)",
            whiteSpace: "pre",
          }}
        >
          {logLines.map((line, index) => (
            <p key={index} style={{ margin: 0 }}>{line}</p>
          ))}
        </div>
        <div style={{ position: "absolute", inset: 0, border: "0.791px solid oklch(1 0 0 / 10%)", borderRadius: "10px", pointerEvents: "none" }} />
      </div>

      <button
        style={{
          position: "absolute",
          top: "calc(50% + 57.6px)",
          left: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "6.375px",
          padding: "5.1px 10.2px",
          background: "oklch(0.94 0 0)",
          color: "oklch(0.1 0 0)",
          border: "none",
          cursor: "pointer",
          borderRadius: "8.925px",
          fontFamily: "'Geist', sans-serif",
          fontSize: "16.575px",
          lineHeight: "25.5px",
          letterSpacing: "-0.51px",
          fontWeight: 500,
          whiteSpace: "nowrap",
        }}
      >
        Apply 3 fixes
      </button>
    </div>
  )
}

export default FixEngine
