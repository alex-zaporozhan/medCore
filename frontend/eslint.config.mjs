import js from "@eslint/js";
import tseslint from "typescript-eslint";
import {
  RESTRICTED_ADMIN_MANTINE_DRAWER_PATH,
  RESTRICTED_PARALLEL_UI_KIT_PATHS,
} from "./eslint-restricted-ui-imports.mjs";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "node_modules",
      "coverage",
      "**/*.config.*",
      "public",
      "playwright-report",
      "test-results",
      "e2e",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-require-imports": "off",
      "@typescript-eslint/no-empty-object-type": "off",
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { paths: [...RESTRICTED_PARALLEL_UI_KIT_PATHS] }],
    },
  },
  {
    files: ["src/admin/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        { paths: [...RESTRICTED_PARALLEL_UI_KIT_PATHS, RESTRICTED_ADMIN_MANTINE_DRAWER_PATH] },
      ],
    },
  }
);
