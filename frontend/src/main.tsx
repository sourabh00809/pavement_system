import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ThemeProvider } from './components/ThemeProvider'
import { Toaster } from 'sonner'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider attribute="class" defaultTheme="dark" disableTransitionOnChange>
        <App />
        <Toaster richColors position="top-right" />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
