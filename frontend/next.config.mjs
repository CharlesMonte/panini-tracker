import os from "node:os";

/** @type {import('next').NextConfig} */
const backendUrl = process.env.NEXT_BACKEND_URL || "http://127.0.0.1:8000";
const localNetworkHosts = Object.values(os.networkInterfaces())
  .flat()
  .filter((address) => address && address.family === "IPv4" && !address.internal)
  .map((address) => address.address);

const nextConfig = {
  allowedDevOrigins: [
    "127.0.0.1",
    "0.0.0.0",
    ...localNetworkHosts,
    ...(process.env.NEXT_ALLOWED_DEV_ORIGINS || "")
      .split(",")
      .map((origin) => origin.trim())
      .filter(Boolean),
  ],
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
