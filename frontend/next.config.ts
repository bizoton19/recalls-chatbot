import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for Railway / self-hosted Node.js deployments
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
