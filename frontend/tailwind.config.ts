import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#020617',
        panel: '#0f172a',
        bull: '#34d399',
        bear: '#f43f5e',
        info: '#22d3ee',
      },
    },
  },
  plugins: [],
} satisfies Config;
