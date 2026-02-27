import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const isDemo = process.env.VITE_DEMO_MODE === 'true'

export default defineConfig({
  base: isDemo ? '/Wingman/' : '/',
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg', 'icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'Wingman Concert Tracker',
        short_name: 'Wingman',
        description: 'Manage artists, venues, and concert tracking for Des Moines area',
        theme_color: '#1e1b4b',
        background_color: '#f8fafc',
        display: 'standalone',
        orientation: 'portrait-primary',
        start_url: isDemo ? '/Wingman/' : '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,json}'],
        // Exclude Spotify OAuth routes from service worker navigation fallback
        // so the browser hits the FastAPI server directly instead of getting the cached SPA
        navigateFallbackDenylist: [/^\/auth\//, /^\/callback/],
        runtimeCaching: isDemo ? [] : [
          {
            urlPattern: /^\/api\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'api-cache', networkTimeoutSeconds: 10 }
          }
        ]
      }
    })
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
