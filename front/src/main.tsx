import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Шрифты лежат в сборке и отдаются нашим сервером — не зависим от доступности Google Fonts.
// Браузер скачивает только нужные наборы символов (кириллица/латиница) по unicode-range.
import '@fontsource/yeseva-one/400.css'
import '@fontsource-variable/manrope/wght.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
