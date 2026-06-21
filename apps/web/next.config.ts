import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    const gatewayUrl = process.env.GATEWAY_URL;
    if (!gatewayUrl && process.env.NODE_ENV !== "development") {
      throw new Error("GATEWAY_URL environment variable is required in non-development environments");
    }
    return [
      {
        source: "/api/:path*",
        destination: `${gatewayUrl ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
