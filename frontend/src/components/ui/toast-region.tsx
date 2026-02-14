import { X } from "lucide-react"

import { useToastStore, type ToastTone } from "@/stores/toast-store"

const toneClasses: Record<ToastTone, string> = {
  success: "border-emerald-500/40 bg-emerald-500/15 text-emerald-900 dark:text-emerald-100",
  error: "border-rose-500/40 bg-rose-500/15 text-rose-900 dark:text-rose-100",
  info: "border-sky-500/40 bg-sky-500/15 text-sky-900 dark:text-sky-100",
}

export function ToastRegion() {
  const toasts = useToastStore((state) => state.toasts)
  const dismissToast = useToastStore((state) => state.dismissToast)

  if (toasts.length === 0) {
    return null
  }

  return (
    <section className="pointer-events-none fixed right-4 top-4 z-[70] flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
      {toasts.map((toast) => (
        <article
          key={toast.id}
          className={`pointer-events-auto rounded-lg border px-3 py-2 shadow-lg backdrop-blur-sm ${toneClasses[toast.tone]}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">{toast.title}</p>
              {toast.description && <p className="mt-1 text-xs opacity-90">{toast.description}</p>}
            </div>
            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              className="rounded-md p-1 opacity-80 hover:bg-black/10 hover:opacity-100 dark:hover:bg-white/10"
              aria-label="Dismiss notification"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </article>
      ))}
    </section>
  )
}
