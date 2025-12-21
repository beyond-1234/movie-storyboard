/** @type {import('tailwindcss').Config} */
export default {
  // 关键：明确指定扫描 Vue 和 JS/TS 文件
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}