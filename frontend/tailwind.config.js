/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Dark industrial control-room. No neon, no gradients.
        base: "#0d0d0f", // app background
        panel: "#161619", // cards
        panel2: "#1c1c20", // raised / inputs
        hair: "#2a2a2f", // hairline borders
        fg: "#e8e6e1", // primary text (warm off-white)
        muted: "#9a958c", // secondary text
        faint: "#6b675f", // tertiary / labels
        crit: "#ef4444", // critical (muted red)
        critdim: "#7f1d1d",
        warn: "#f59e0b", // warning (amber)
        warndim: "#78350f",
        steel: "#7c8694", // neutral data / healthy
      },
      fontFamily: {
        mono: [
          "ui-monospace",
          "JetBrains Mono",
          "Cascadia Code",
          "SF Mono",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
