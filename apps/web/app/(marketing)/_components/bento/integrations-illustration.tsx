import type React from "react"

const IntegrationsIllustration: React.FC = () => {
  const LogoBox: React.FC<{ logoSvg?: React.ReactNode; isGradientBg?: boolean }> = ({ logoSvg, isGradientBg }) => {
    const boxStyle: React.CSSProperties = {
      width: "60px",
      height: "60px",
      position: "relative",
      borderRadius: "9px",
      border: "1px solid oklch(1 0 0 / 10%)",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      overflow: "hidden",
      flexShrink: 0,
    }

    if (isGradientBg) {
      boxStyle.background = "linear-gradient(180deg, oklch(1 0 0 / 20%) 0%, transparent 100%)"
      boxStyle.boxShadow = "0px 1px 2px rgba(0,0,0,0.12)"
      boxStyle.backdropFilter = "blur(18px)"
      boxStyle.padding = "6px 8px"
    }

    return (
      <div style={boxStyle}>
        {logoSvg && (
          <div style={{ width: "36px", height: "36px", position: "relative", overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "center" }}>
            {logoSvg}
          </div>
        )}
      </div>
    )
  }

  const GitHubLogo = (
    <svg width="36" height="37" viewBox="0 0 36 37" fill="none" xmlns="http://www.w3.org/2000/svg">
      <g clipPath="url(#clip-github)">
        <path fillRule="evenodd" clipRule="evenodd" d="M18 0.111328C8.055 0.111328 0 8.16633 0 18.1113C0 26.0763 5.1525 32.8038 12.3075 35.1888C13.2075 35.3463 13.545 34.8063 13.545 34.3338C13.545 33.9063 13.5225 32.4888 13.5225 30.9813C9 31.8138 7.83 29.8788 7.47 28.8663C7.2675 28.3488 6.39 26.7513 5.625 26.3238C4.995 25.9863 4.095 25.1538 5.6025 25.1313C7.02 25.1088 8.0325 26.4363 8.37 26.9763C9.99 29.6988 12.5775 28.9338 13.6125 28.4613C13.77 27.2913 14.2425 26.5038 14.76 26.0538C10.755 25.6038 6.57 24.0513 6.57 17.1663C6.57 15.2088 7.2675 13.5888 8.415 12.3288C8.235 11.8788 7.605 10.0338 8.595 7.55883C8.595 7.55883 10.1025 7.08633 13.545 9.40383C14.985 8.99883 16.515 8.79633 18.045 8.79633C19.575 8.79633 21.105 8.99883 22.545 9.40383C25.9875 7.06383 27.495 7.55883 27.495 7.55883C28.485 10.0338 27.855 11.8788 27.675 12.3288C28.8225 13.5888 29.52 15.1863 29.52 17.1663C29.52 24.0738 25.3125 25.6038 21.3075 26.0538C21.96 26.6163 22.5225 27.6963 22.5225 29.3838C22.5225 31.7913 22.5 33.7263 22.5 34.3338C22.5 34.8063 22.8375 35.3688 23.7375 35.1888C30.8475 32.8038 36 26.0538 36 18.1113C36 8.16633 27.945 0.111328 18 0.111328Z" fill="oklch(0.85 0 0)" />
      </g>
      <defs><clipPath id="clip-github"><rect width="36" height="36" fill="white" transform="translate(0 0.111328)" /></clipPath></defs>
    </svg>
  )

  const LinearLogo = (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="18" cy="18" r="14" stroke="oklch(0.85 0 0)" strokeWidth="2" fill="none" />
      <path d="M10 26L26 10M10 18L18 10M18 26L26 18" stroke="oklch(0.85 0 0)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )

  const SlackLogo = (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M13.5 8C13.5 6.343 14.843 5 16.5 5C18.157 5 19.5 6.343 19.5 8V13.5H16.5C14.843 13.5 13.5 12.157 13.5 10.5V8Z" fill="oklch(0.85 0 0)" opacity="0.8" />
      <path d="M5 16.5C5 14.843 6.343 13.5 8 13.5H13.5V16.5C13.5 18.157 12.157 19.5 10.5 19.5H8C6.343 19.5 5 18.157 5 16.5Z" fill="oklch(0.85 0 0)" opacity="0.8" />
      <path d="M22.5 28C22.5 29.657 21.157 31 19.5 31C17.843 31 16.5 29.657 16.5 28V22.5H19.5C21.157 22.5 22.5 23.843 22.5 25.5V28Z" fill="oklch(0.85 0 0)" opacity="0.8" />
      <path d="M31 19.5C31 21.157 29.657 22.5 28 22.5H22.5V19.5C22.5 17.843 23.843 16.5 25.5 16.5H28C29.657 16.5 31 17.843 31 19.5Z" fill="oklch(0.85 0 0)" opacity="0.8" />
    </svg>
  )

  const JiraLogo = (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 5L31 18L18 31L5 18L18 5Z" stroke="oklch(0.85 0 0)" strokeWidth="2" fill="none" />
      <path d="M18 11L25 18L18 25L11 18L18 11Z" fill="oklch(0.85 0 0)" opacity="0.6" />
    </svg>
  )

  const VSCodeLogo = (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M5 12L18 6L31 12V24L18 30L5 24V12Z" stroke="oklch(0.85 0 0)" strokeWidth="2" fill="none" />
      <path d="M5 12L18 18L31 12M18 18V30" stroke="oklch(0.85 0 0)" strokeWidth="2" />
    </svg>
  )

  const gridItems = Array(40).fill(null).map((_, i) => {
    const item: { logoSvg?: React.ReactNode; isGradientBg?: boolean } = {}
    const row = Math.floor(i / 10)
    const col = i % 10
    if (row === 0 && col === 3) { item.logoSvg = GitHubLogo; item.isGradientBg = true }
    else if (row === 1 && col === 5) { item.logoSvg = LinearLogo; item.isGradientBg = true }
    else if (row === 2 && col === 3) { item.logoSvg = SlackLogo; item.isGradientBg = true }
    else if (row === 2 && col === 7) { item.logoSvg = JiraLogo; item.isGradientBg = true }
    else if (row === 3 && col === 5) { item.logoSvg = VSCodeLogo; item.isGradientBg = true }
    return item
  })

  return (
    <div className="w-full h-full relative" role="img" aria-label="Integration connectors grid">
      <div style={{ width: "377.33px", height: "278.08px", left: "0px", top: "24px", position: "absolute", background: "radial-gradient(ellipse 103.87% 77.04% at 52.56% -1.80%, transparent 0%, oklch(0.85 0 0 / 96%) 15%, oklch(0.85 0 0 / 40%) 49%, oklch(0.85 0 0 / 96%) 87%, transparent 100%)" }} />
      <div style={{ width: "377px", height: "265px", left: "0.34px", top: "43.42px", position: "absolute", backdropFilter: "blur(7.91px)", display: "flex", flexDirection: "column", justifyContent: "flex-start", alignItems: "center", gap: "16px" }}>
        {Array.from({ length: 4 }).map((_, rowIndex) => (
          <div key={rowIndex} style={{ display: "flex", justifyContent: "flex-start", alignItems: "center", gap: "16px" }}>
            {gridItems.slice(rowIndex * 10, (rowIndex + 1) * 10).map((item, colIndex) => (
              <LogoBox key={colIndex} {...item} />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export default IntegrationsIllustration
