import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        selisih: {
          bg: "#FAF8F5",
          card: "#FFFFFF",
          sidebar: "#F3EFE8",
          border: "#DDD8CD",
          borderDark: "#C8C2B5",
          text: "#1A1917",
          title: "#111110",
          muted: "#4A4843",
          tag: "#EFECE6",
          primary: "#1A1917",
          primaryHover: "#2D2C28",
          successBg: "#E6F4EA",
          successText: "#0F5C2B",
          successBorder: "#A3D4B0",
          dangerBg: "#FCE8E6",
          dangerText: "#C5221F",
          dangerBorder: "#F4B3AE",
          warningBg: "#FEF3D6",
          warningText: "#8A5B00",
          warningBorder: "#F5D68B",
          blueAccent: "#0f62fe",
        },
      },
    },
  },
  plugins: [],
};

export default config;
