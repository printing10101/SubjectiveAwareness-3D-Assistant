import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import viteCompression from 'vite-plugin-compression'

export default defineConfig({
  plugins: [
    vue(),
    // Gzip 压缩
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 10240, // 超过 10KB 的文件才压缩
    }),
    // Brotli 压缩（更好的压缩率）
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 10240,
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 目标浏览器版本
    target: 'es2015',
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 生成 sourcemap（生产环境可关闭以提升构建速度）
    sourcemap: false,
    // 压缩选项（使用 Vite 内置的 esbuild，无需额外安装 terser）
    minify: 'esbuild',
    // 代码分割策略
    rollupOptions: {
      output: {
        // 手动分割第三方库
        manualChunks: {
          // Vue 核心库
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // UI 组件库
          'ui-vendor': ['element-plus'],
          // 图表库
          'chart-vendor': ['echarts', 'vue-echarts', 'd3'],
          // 工具库
          'utils-vendor': ['axios', 'file-saver', 'html2canvas', 'jspdf'],
          // 编辑器
          'editor-vendor': ['md-editor-v3', 'marked'],
          // 监控
          'monitor-vendor': ['@sentry/vue'],
        },
        // 资源文件命名
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      },
    },
    // 动态导入块大小警告阈值（500KB）
    chunkSizeWarningLimit: 500,
    // 资源内联阈值（4KB）
    assetsInlineLimit: 4096,
    // 预加载生成
    modulePreload: {
      polyfill: false,
    },
  },
  // 优化依赖预构建
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'axios'],
    exclude: ['@sentry/vue'],
  },
})
