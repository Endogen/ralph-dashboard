import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import { App } from "@/App"
import { applyInitialTheme } from "@/hooks/use-theme"
import "@/index.css"

applyInitialTheme()

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
