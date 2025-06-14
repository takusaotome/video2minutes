module.exports = {
  // 基本設定
  semi: false,
  singleQuote: true,
  quoteProps: 'as-needed',
  trailingComma: 'none',
  bracketSpacing: true,
  bracketSameLine: false,
  arrowParens: 'avoid',
  
  // インデント設定
  tabWidth: 2,
  useTabs: false,
  
  // 行の長さ
  printWidth: 80,
  
  // 改行設定
  endOfLine: 'lf',
  
  // Vue.js 固有設定
  vueIndentScriptAndStyle: false,
  
  // ファイル別設定
  overrides: [
    {
      files: '*.vue',
      options: {
        parser: 'vue'
      }
    },
    {
      files: '*.json',
      options: {
        parser: 'json',
        trailingComma: 'none'
      }
    },
    {
      files: '*.md',
      options: {
        parser: 'markdown',
        printWidth: 100,
        proseWrap: 'always'
      }
    },
    {
      files: '*.yaml',
      options: {
        parser: 'yaml',
        tabWidth: 2
      }
    },
    {
      files: '*.yml',
      options: {
        parser: 'yaml',
        tabWidth: 2
      }
    }
  ]
} 