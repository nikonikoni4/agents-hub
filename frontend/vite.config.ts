import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // 加载环境变量（VITE_ 前缀的变量会暴露给客户端）
  const env = loadEnv(mode, process.cwd(), '');

  const devServerPort = parseInt(env.VITE_DEV_PORT || '5173', 10);
  const apiPort = parseInt(env.VITE_API_PORT || '8099', 10);

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: devServerPort,
      proxy: {
        '/api': {
          target: `http://localhost:${apiPort}`,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  };
});
