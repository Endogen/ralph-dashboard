/**
 * What to do when the server closes a websocket with 1008 (auth refused).
 *
 * Reconnecting with the token the server just rejected is a hot loop, and
 * treating every refusal as transient leaves a dead socket with no prompt to
 * sign in again. Keeping the decision here makes both cases testable without a
 * React renderer.
 */
export type AuthRecoveryAction =
  | { kind: "reconnect"; token: string }
  | { kind: "sign-out" }
  | { kind: "retry-later" }

export async function planAuthRecovery(
  attempt: number,
  maxRetries: number,
  refresh: () => Promise<string | null>,
): Promise<AuthRecoveryAction> {
  // The token may simply have expired, so a bounded number of refreshes is
  // worth trying. Past that, the server is rejecting us for another reason.
  if (attempt > maxRetries) {
    return { kind: "sign-out" }
  }
  let token: string | null
  try {
    token = await refresh()
  } catch {
    // Network or 5xx: the session may still be good. Back off and retry.
    return { kind: "retry-later" }
  }
  // A resolved null means the refresh endpoint refused us: the session is over.
  return token ? { kind: "reconnect", token } : { kind: "sign-out" }
}
