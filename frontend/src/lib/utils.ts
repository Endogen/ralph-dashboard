import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Convert k-tokens (thousands of tokens) to actual token count for display.
 * The backend stores and returns token values in k-tokens (e.g. 67.126 = 67,126 tokens).
 * Cost calculations use k-tokens directly (tokens * cost_per_1k), so only multiply for display.
 */
export function displayTokens(kTokens: number): number {
  return Math.round(kTokens * 1000)
}
