import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('../../src/frontend/src', import.meta.url))
    }
  },
  
  test: {
    globals: true,
    environment: 'jsdom',
    
    // テストファイルのパターン
    include: [
      '**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
      '**/tests/**/*.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    
    // モックの設定
    setupFiles: ['./setup.js'],
    
    // カバレッジ設定
    coverage: {
      provider: 'c8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.config.js',
        '**/setup.js',
        '**/*.d.ts'
      ],
      all: true,
      src: ['../../src/frontend/src']
    },
    
    // テストタイムアウト
    testTimeout: 10000,
    hookTimeout: 10000,
    
    // 並行実行設定
    threads: true,
    maxThreads: 4,
    minThreads: 1,
    
    // レポーター設定
    reporter: ['verbose', 'json', 'html'],
    
    // ウォッチモード除外
    watchExclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/coverage/**'
    ]
  }
})