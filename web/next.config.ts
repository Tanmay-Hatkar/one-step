import type { NextConfig } from "next";

// Error reports are tagged with the build they came from. Vercel sets these at build
// time; locally they're empty and the fallbacks apply.
const RELEASE =
  process.env.VERCEL_GIT_COMMIT_SHA || process.env.VERCEL_DEPLOYMENT_ID || "dev";
const APP_ENV = process.env.NEXT_PUBLIC_APP_ENV || process.env.VERCEL_ENV || "development";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_RELEASE: RELEASE,
    NEXT_PUBLIC_APP_ENV: APP_ENV,
  },
  cacheComponents: true,
  partialPrefetching: true,
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
