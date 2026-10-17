import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

// Production: static export served by FastAPI on the same origin (PLAN §3).
// Development: `next dev` proxies /api/* to the backend on :8000, since
// rewrites are not supported together with `output: "export"`.
const nextConfig: NextConfig = {
  ...(isDev
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/:path*`,
            },
          ];
        },
      }
    : { output: "export" }),
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
