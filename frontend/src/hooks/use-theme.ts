import { useCallback, useEffect, useMemo, useState } from "react"

export type ThemePreference = "light" | "dark" | "system"
export type ResolvedTheme = "light" | "dark"

const STORAGE_KEY = "ralph-dashboard-theme"
const DARK_MEDIA_QUERY = "(prefers-color-scheme: dark)"

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") {
    return "dark"
  }
  return window.matchMedia(DARK_MEDIA_QUERY).matches ? "dark" : "light"
}

function readStoredPreference(): ThemePreference {
  if (typeof window === "undefined") {
    return "system"
  }
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored
  }
  return "system"
}

function resolveTheme(preference: ThemePreference, systemTheme: ResolvedTheme): ResolvedTheme {
  if (preference === "system") {
    return systemTheme
  }
  return preference
}

function applyThemeClass(theme: ResolvedTheme): void {
  if (typeof document === "undefined") {
    return
  }
  document.documentElement.classList.toggle("dark", theme === "dark")
}

export function applyInitialTheme(): void {
  const preference = readStoredPreference()
  const resolved = resolveTheme(preference, getSystemTheme())
  applyThemeClass(resolved)
}

export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(() => readStoredPreference())
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(() => getSystemTheme())

  useEffect(() => {
    const media = window.matchMedia(DARK_MEDIA_QUERY)
    const handleChange = (event: MediaQueryListEvent) => {
      setSystemTheme(event.matches ? "dark" : "light")
    }

    media.addEventListener("change", handleChange)
    return () => {
      media.removeEventListener("change", handleChange)
    }
  }, [])

  const resolvedTheme = useMemo(
    () => resolveTheme(preference, systemTheme),
    [preference, systemTheme],
  )

  useEffect(() => {
    if (preference === "system") {
      window.localStorage.removeItem(STORAGE_KEY)
    } else {
      window.localStorage.setItem(STORAGE_KEY, preference)
    }
  }, [preference])

  useEffect(() => {
    applyThemeClass(resolvedTheme)
  }, [resolvedTheme])

  const toggleTheme = useCallback(() => {
    setPreference((current) => {
      const currentResolved = current === "system" ? getSystemTheme() : current
      return currentResolved === "dark" ? "light" : "dark"
    })
  }, [])

  return {
    preference,
    resolvedTheme,
    setPreference,
    toggleTheme,
  }
}
