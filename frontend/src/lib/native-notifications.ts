import { showBrowserNotification } from "@/lib/browser-notifications"
import { useToastStore, type ToastTone } from "@/stores/toast-store"

type AttentionSignalInput = {
  title: string
  description?: string
  tone?: ToastTone
  durationMs?: number
  dedupeKey?: string
  browserTag?: string
  onClick?: () => void
}

const deliveredSignals = new Map<string, number>()
const SIGNAL_DEDUPE_WINDOW_MS = 60_000

function isDocumentVisible(): boolean {
  if (typeof document === "undefined") {
    return true
  }
  return document.visibilityState === "visible"
}

function markSignalDelivered(dedupeKey: string | undefined): boolean {
  if (!dedupeKey) {
    return true
  }

  const now = Date.now()
  for (const [key, timestamp] of deliveredSignals.entries()) {
    if (now - timestamp > SIGNAL_DEDUPE_WINDOW_MS) {
      deliveredSignals.delete(key)
    }
  }

  const previous = deliveredSignals.get(dedupeKey)
  if (previous && now - previous < SIGNAL_DEDUPE_WINDOW_MS) {
    return false
  }

  deliveredSignals.set(dedupeKey, now)
  return true
}

export async function deliverAttentionSignal({
  title,
  description,
  tone = "info",
  durationMs,
  dedupeKey,
  browserTag,
  onClick,
}: AttentionSignalInput): Promise<"toast" | "browser" | "none"> {
  if (!markSignalDelivered(dedupeKey)) {
    return "none"
  }

  if (!isDocumentVisible()) {
    const shown = await showBrowserNotification({
      title,
      body: description,
      tag: browserTag ?? dedupeKey,
      onClick,
    })
    if (shown) {
      return "browser"
    }
  }

  useToastStore.getState().pushToast({
    title,
    description,
    tone,
    durationMs,
    dedupeKey,
  })
  return "toast"
}
