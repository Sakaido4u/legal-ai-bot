module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
    'prettier', // Must be last — disables ESLint rules that conflict with Prettier
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    // Allow empty arrow functions (common for placeholder handlers)
    '@typescript-eslint/no-empty-function': 'warn',
    // Warn on unused vars but don't error (you'll have stubs early on)
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    // React 17+ doesn't need React in scope for JSX
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
  },
}