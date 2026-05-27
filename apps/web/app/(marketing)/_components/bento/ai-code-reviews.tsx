import type React from "react"

const AiCodeReviews: React.FC = () => {
  const themeVars = {
    "--ai-primary-color": "var(--color-foreground)",
    "--ai-background-color": "oklch(0.1 0 0)",
    "--ai-text-color": "var(--color-foreground)",
    "--ai-text-dark": "oklch(0.1 0 0)",
    "--ai-border-color": "oklch(1 0 0 / 10%)",
    "--ai-border-main": "oklch(1 0 0 / 10%)",
    "--ai-highlight-primary": "oklch(1 0 0 / 5%)",
    "--ai-highlight-header": "oklch(1 0 0 / 8%)",
  }

  return (
    <div
      style={
        {
          width: "100%",
          height: "100%",
          position: "relative",
          background: "transparent",
          ...themeVars,
        } as React.CSSProperties
      }
      role="img"
      aria-label="AI Code Reviews interface showing code suggestions with apply buttons"
    >
      <div
        style={{
          position: "absolute",
          top: "30px",
          left: "50%",
          transform: "translateX(-50%) scale(0.9)",
          width: "340px",
          height: "205.949px",
          background: "linear-gradient(180deg, var(--ai-background-color) 0%, transparent 100%)",
          opacity: 0.6,
          borderRadius: "8.826px",
          border: "0.791px solid var(--ai-border-color)",
          overflow: "hidden",
          backdropFilter: "blur(16px)",
        }}
      >
        <div
          style={{
            padding: "7.355px 8.826px",
            height: "100%",
            boxSizing: "border-box",
            overflow: "hidden",
            background: "oklch(0.12 0 0)",
            borderRadius: "8px",
          }}
        >
          <div
            style={{
              fontFamily: "'Geist Mono', 'SF Mono', Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
              fontSize: "9.562px",
              lineHeight: "14.711px",
              letterSpacing: "-0.2942px",
              color: "oklch(0.5 0 0)",
              width: "100%",
              maxWidth: "320px",
              margin: 0,
            }}
          >
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"async fn review_pr(diff: &str) {"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{" let agents = vec!["}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   SecurityAgent::new(),"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   QualityAgent::new(),"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   TestingAgent::new(),"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{" ];"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   let findings ="}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"     join_all(agents).await;"}</p>
          </div>
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: "51.336px",
          left: "50%",
          transform: "translateX(-50%)",
          width: "340px",
          height: "221.395px",
          background: "oklch(0.1 0 0)",
          backdropFilter: "blur(16px)",
          borderRadius: "9.488px",
          border: "1px solid var(--ai-border-main)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "9.488px",
            height: "100%",
            boxSizing: "border-box",
            position: "relative",
            overflow: "hidden",
            background: "oklch(0.12 0 0)",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              width: "100%",
              top: "47.67px",
              height: "33.118px",
              background: "oklch(1 0 0 / 8%)",
              zIndex: 1,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              width: "100%",
              top: "80.791px",
              height: "45.465px",
              background: "oklch(1 0 0 / 5%)",
              zIndex: 1,
            }}
          />
          <div
            style={{
              fontFamily: "'Geist Mono', 'SF Mono', Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
              fontSize: "10.279px",
              lineHeight: "15.814px",
              letterSpacing: "-0.3163px",
              color: "oklch(0.85 0 0)",
              width: "100%",
              maxWidth: "320px",
              position: "relative",
              zIndex: 2,
              margin: 0,
            }}
          >
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"async fn review_pr(diff: &str) {"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{" let agents = vec!["}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   SecurityAgent::new(),"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   QualityAgent::new(),"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   TestingAgent::new(),"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{" ];"}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"   let findings ="}</p>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", fontWeight: 400 }}>{"     join_all(agents).await;"}</p>
          </div>
          <button
            style={{
              position: "absolute",
              top: "calc(50% + 29.745px)",
              right: "20px",
              transform: "translateY(-50%)",
              zIndex: 3,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "3.953px",
              background: "oklch(0.94 0 0)",
              color: "oklch(0.1 0 0)",
              border: "none",
              cursor: "pointer",
              fontWeight: 500,
              whiteSpace: "nowrap",
              transition: "all 0.2s ease",
              padding: "3.163px 6.326px",
              borderRadius: "5.535px",
              fontSize: "10.279px",
              lineHeight: "15.814px",
              letterSpacing: "-0.3163px",
            }}
          >
            <span style={{ fontFamily: "'Geist', sans-serif", fontWeight: 500 }}>Apply fix</span>
            <span style={{ fontFamily: "'SF Pro', system-ui, sans-serif", fontWeight: 500 }}>⌘Y</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default AiCodeReviews
