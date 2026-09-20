import { describe, expect, it, vi } from "vitest"

import { planAuthRecovery } from "./websocket-auth-recovery"

describe("planAuthRecovery", () => {
  it("reconnects when the refresh returns a new token", async () => {
    const action = await planAuthRecovery(1, 2, vi.fn().mockResolvedValue("fresh-token"))
    expect(action).toEqual({ kind: "reconnect", token: "fresh-token" })
  })

  it("signs out when the refresh is refused rather than reconnecting", async () => {
    // refreshAccessToken resolves null on a refusal; it does not throw.
    const refresh = vi.fn().mockResolvedValue(null)
    expect(await planAuthRecovery(1, 2, refresh)).toEqual({ kind: "sign-out" })
    expect(refresh).toHaveBeenCalledOnce()
  })

  it("retries later when the refresh fails transiently", async () => {
    const action = await planAuthRecovery(1, 2, vi.fn().mockRejectedValue(new Error("network")))
    expect(action).toEqual({ kind: "retry-later" })
  })

  it("stops refreshing once the retry budget is spent", async () => {
    const refresh = vi.fn().mockResolvedValue("token-the-server-keeps-rejecting")
    expect(await planAuthRecovery(3, 2, refresh)).toEqual({ kind: "sign-out" })
    expect(refresh).not.toHaveBeenCalled()
  })
})
