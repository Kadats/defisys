import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/ws/:path*',
        destination: 'http://backend:8000/api/ws/:path*',
      },
    ];
  },
};

export default nextConfig;
