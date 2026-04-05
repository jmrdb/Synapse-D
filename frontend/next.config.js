/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/health",
        destination: "http://localhost:8000/health",
      },
      {
        source: "/files/:path*",
        destination: "http://localhost:8000/files/:path*",
      },
    ];
  },
  webpack: (config, { isServer }) => {
    // Niivue uses daikon which requires 'fs' — only available server-side
    // Since Niivue runs client-only (WebGL), we polyfill with empty module
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
