import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { applyInitialTheme, useTheme } from "./use-theme"

let root: Root | undefined
let container: HTMLDivElement
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true)
  vi.stubGlobal("matchMedia", () => ({ matches: true, addEventListener() {}, removeEventListener() {} }))
  container = document.createElement("div")
  document.body.append(container)
})
afterEach(async () => {
  await act(async () => root?.unmount())
  root = undefined
  container.remove()
  document.documentElement.classList.remove("dark")
  vi.unstubAllGlobals()
})

it.each(["unavailable", "blocked"])("keeps theme switching usable when storage is %s", async (mode) => {
  const blocked = () => { throw new DOMException("Storage disabled", "SecurityError") }
  vi.stubGlobal("localStorage", mode === "unavailable" ? undefined : {
    getItem: blocked, setItem: blocked, removeItem: blocked,
  })
  expect(() => applyInitialTheme()).not.toThrow()
  expect(document.documentElement.classList.contains("dark")).toBe(true)
  function Consumer() {
    const { resolvedTheme, toggleTheme } = useTheme()
    return <button onClick={toggleTheme}>{resolvedTheme}</button>
  }
  await act(async () => { root = createRoot(container); root.render(<Consumer />) })
  expect(container.textContent).toBe("dark")
  await act(async () => container.querySelector("button")!.click())
  expect(container.textContent).toBe("light")
  expect(document.documentElement.classList.contains("dark")).toBe(false)
})
