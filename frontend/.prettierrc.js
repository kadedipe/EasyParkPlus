// ============================================
// PRETTIER CONFIGURATION - PARKING MANAGEMENT SYSTEM FRONTEND
// ============================================

module.exports = {
  // Line length
  printWidth: 100,
  
  // Indentation
  tabWidth: 2,
  useTabs: false,
  
  // Semicolons
  semi: true,
  
  // Quotes
  singleQuote: true,
  quoteProps: 'as-needed',
  jsxSingleQuote: false,
  
  // Commas
  trailingComma: 'es5',
  
  // Brackets
  bracketSpacing: true,
  bracketSameLine: false,
  arrowParens: 'always',
  
  // Whitespace
  proseWrap: 'preserve',
  htmlWhitespaceSensitivity: 'css',
  
  // Line endings
  endOfLine: 'lf',
  
  // Embedded languages
  embeddedLanguageFormatting: 'auto',
  
  // JSX
  singleAttributePerLine: false,
  
  // Experimental
  experimentalTernaries: false,
  
  // Overrides for specific file types
  overrides: [
    {
      files: '*.json',
      options: {
        printWidth: 200,
        trailingComma: 'none',
      },
    },
    {
      files: '*.{yml,yaml}',
      options: {
        singleQuote: false,
        tabWidth: 2,
      },
    },
    {
      files: '*.md',
      options: {
        printWidth: 80,
        proseWrap: 'always',
        embeddedLanguageFormatting: 'off',
      },
    },
    {
      files: '*.{css,scss,less}',
      options: {
        singleQuote: false,
      },
    },
    {
      files: '*.{graphql,gql}',
      options: {
        printWidth: 80,
      },
    },
    {
      files: '*.svg',
      options: {
        parser: 'html',
      },
    },
  ],
};