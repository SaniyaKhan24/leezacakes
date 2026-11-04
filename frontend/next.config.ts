import type { NextConfig } from "next";

/**
 * The browser talks to Django through this origin (`/api`, `/media`, `/health`),
 * so session cookies for guest carts are first-party and no CORS is needed.
 */
const backend = (process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  cacheComponents: true,
  devIndicators: false,
  // Don't generate an AGENTS.md into the project on every dev start.
  agentRules: false,
  partialPrefetching: true,
  // Django routes end in a slash; let them through untouched.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    // `:path*` drops a trailing slash, so slash-terminated URLs get their own rule.
    return [
      { source: "/api/:path*/", destination: `${backend}/api/:path*/` },
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/media/:path*", destination: `${backend}/media/:path*` },
      { source: "/health/:path*", destination: `${backend}/health/:path*` },
      // Staff alerts link into the Django admin; serve it from this origin too.
      { source: "/admin/:path*/", destination: `${backend}/admin/:path*/` },
      { source: "/admin/:path*", destination: `${backend}/admin/:path*` },
      { source: "/admin", destination: `${backend}/admin/` },
      { source: "/static/:path*", destination: `${backend}/static/:path*` },
    ];
  },
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
