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
  plugins: [
      function ({ addBase }) {
          addBase({
              ".el-button": {
                  "background-color": "var(--el-button-bg-color,var(--el-color-white))"
              }
          });
      }
  ]
}