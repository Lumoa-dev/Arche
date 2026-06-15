/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'
import { visualizer } from 'rollup-plugin-visualizer'
import compression from 'vite-plugin-compression'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  const isProduction = env.VITE_NODE_ENV === 'production'
  const apiBaseUrl = env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [
      vue(),

      // 自动导入API
      AutoImport({
        imports: [
          'vue',
          'vue-router',
          'pinia',
          {
            'naive-ui': ['useDialog', 'useMessage', 'useNotification', 'useLoadingBar']
          }
        ],
        dts: 'src/auto-imports.d.ts'
      }),

      // 自动导入组件
      Components({
        dts: 'src/components.d.ts',
        resolvers: [NaiveUiResolver()],
        dirs: ['src/components']
      }),

      // 生产环境构建压缩
      isProduction &&
        compression({
          algorithm: 'gzip',
          threshold: 10240, // 大于10k的文件压缩
          ext: '.gz',
          deleteOriginFile: false
        }),

      // 打包体积分析（只有在build的时候生成分析报告
      isProduction &&
        visualizer({
          filename: 'dist/stats.html',
          open: false,
          gzipSize: true,
          brotliSize: true
        })
    ].filter(Boolean), // 过滤掉false的插件

    // 路径别名
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@/core': resolve(__dirname, 'src/core'),
        '@/hooks': resolve(__dirname, 'src/hooks'),
        '@/lib/types': resolve(__dirname, 'src/lib/types'),
        '@/lib/services': resolve(__dirname, 'src/lib/services'),
        '@/lib/store': resolve(__dirname, 'src/lib/store'),
        '@/lib/router': resolve(__dirname, 'src/lib/router'),
        '@/lib/utils': resolve(__dirname, 'src/lib/utils'),
        '@/lib/composables': resolve(__dirname, 'src/lib/composables'),
        '@/lib/directives': resolve(__dirname, 'src/lib/directives'),
        '@/components': resolve(__dirname, 'src/components'),
        '@/layouts': resolve(__dirname, 'src/layouts'),
        '@/views': resolve(__dirname, 'src/views'),
        '@/plugins': resolve(__dirname, 'src/plugins'),
        '@/assets': resolve(__dirname, 'src/assets'),
        '@/styles': resolve(__dirname, 'src/styles')
      }
    },

    // 开发服务器配置
    server: {
      host: true, // 监听所有地址
      port: 5173,
      open: true, // 自动打开浏览器
      proxy: {
        // API代理：后端路由均挂载在 /api 前缀下（如 /api/auth/login），
        // 前端 baseURL 也是 /api，所以请求路径为 /api/auth/login，
        // 代理直接透传到后端，不做 rewrite
        '/api': {
          target: apiBaseUrl,
          changeOrigin: true
        }
      },
      // 热更新配置
      hmr: {
        overlay: true // 错误浮层
      }
    },

    // 构建配置
    build: {
      target: 'esnext', // 目标环境
      outDir: 'dist', // 输出目录
      assetsDir: 'assets', // 静态资源目录
      sourcemap: !isProduction, // 非生产环境生成sourcemap
      minify: isProduction ? 'esbuild' : false, // 生产环境压缩
      cssMinify: isProduction, // CSS压缩
      // 代码分割策略
      rollupOptions: {
        output: {
          // 分类打包
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
          // 第三方库单独打包（简化配置，避免类型错误
          manualChunks: (id) => {
            if (id.includes('node_modules')) {
              return 'vendor'
            }
          }
        }
      },
      // 小于10k的资源转base64
      assetsInlineLimit: 10240,
      // 关闭生产环境告警
      reportCompressedSize: false,
      // 块大小警告限制
      chunkSizeWarningLimit: 1000
    },

    // 预构建优化
    optimizeDeps: {
      include: ['vue', 'vue-router', 'pinia', 'naive-ui'],
      force: false
    },

    // 测试配置
    test: {
      globals: false,
      environment: 'jsdom',
      include: ['src/tests/**/*.{test,spec}.{ts,js}'],
      css: true,
      setupFiles: ['./vitest.setup.ts'],
      coverage: {
        provider: 'v8',
        reporter: ['text'],
        include: ['src/**/*.ts'],
        exclude: [
          'src/**/*.d.ts',
          'src/**/__tests__/**',
          'src/**/generated.d.ts',
          'src/auto-imports.d.ts',
          'src/components.d.ts',
          'src/env.d.ts',
          'src/**/index.ts'
        ],
        thresholds: {
          statements: 80,
          branches: 75,
          functions: 65,
          lines: 80
        }
      }
    },

    // CSS预处理器配置
    css: {
      preprocessorOptions: {
        // 可以在这里配置less/sass等预处理器
      },
      // CSS代码拆分
      codeSplit: true
    }
  }
})
