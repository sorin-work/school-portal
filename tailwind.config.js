/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./school_portal/templates/**/*.html", "./school_portal/static/js/**/*.js"],
  safelist: [{ pattern: /badge-(slate|sky|amber|indigo|stone|pink|emerald|orange|red)/ }],
  theme: {
    extend: {
      minHeight: { 12: "3rem", 24: "6rem" },
    },
  },
  plugins: [],
};
