/**
 * PostCSS config for Mantine v7 only. No Tailwind.
 * Required by Mantine so that @mantine/core/styles.css is processed correctly.
 * @see https://v7.mantine.dev/guides/vite/
 */
module.exports = {
  plugins: {
    "postcss-preset-mantine": {},
    "postcss-simple-vars": {
      variables: {
        "mantine-breakpoint-xs": "36em",
        "mantine-breakpoint-sm": "48em",
        "mantine-breakpoint-md": "62em",
        "mantine-breakpoint-lg": "75em",
        "mantine-breakpoint-xl": "88em",
      },
    },
  },
};
