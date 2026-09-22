import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Recharts and the QR renderer are the two heavy dependencies here and
        // neither is needed to paint the first screen: the chart is lazy inside
        // HabitCard, and the QR route never loads at all inside Telegram.
        // Pinning them to their own chunks keeps them out of the entry bundle.
        manualChunks(id: string) {
          if (id.includes('node_modules/recharts') || id.includes('node_modules/d3-')) {
            return 'recharts'
          }
          if (id.includes('node_modules/qrcode.react')) return 'qr'
          return undefined
        },
      },
    },
  },
})
