import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [react()],
    
    server: {
      port: parseInt(env.VITE_DEV_SERVER_PORT || '3000'),
      host: env.VITE_DEV_SERVER_HOST || true,
      open: env.VITE_DEV_SERVER_OPEN === 'true',
      https: env.VITE_DEV_SERVER_HTTPS === 'true',
      cors: env.VITE_DEV_SERVER_CORS === 'true',
      
      proxy: {
        [env.VITE_PROXY_API || '/api']: {
          target: env.VITE_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: env.VITE_PROXY_CHANGE_ORIGIN === 'true',
          secure: env.VITE_PROXY_SECURE === 'true',
        },
        [env.VITE_PROXY_WS || '/ws']: {
          target: env.VITE_PROXY_TARGET?.replace('http', 'ws') || 'ws://localhost:8000',
          ws: true,
        },
      },
    },
    
    build: {
      outDir: 'dist',
      sourcemap: env.VITE_APP_ENV !== 'production',
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: env.VITE_APP_ENV === 'production',
          drop_debugger: env.VITE_APP_ENV === 'production',
        },
      },
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom', 'react-router-dom'],
            mui: ['@mui/material', '@emotion/react', '@emotion/styled'],
            maps: ['@react-google-maps/api'],
            forms: ['react-hook-form', 'zod'],
            charts: ['recharts'],
          },
        },
      },
    },
    
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
      },
    },
    
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version),
    },
  };
});