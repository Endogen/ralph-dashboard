import { Fragment, isValidElement } from "react"

// Minimal compatibility shim for Recharts in environments where `react-is`
// cannot be installed from npm during build.
export function isFragment(value: unknown): boolean {
  return isValidElement(value) && value.type === Fragment
}
