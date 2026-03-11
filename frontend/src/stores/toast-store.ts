import { create } from "zustand"

export type ToastTone = "success" | "error" | "info"

export type ToastEntry = {
  id: number
  title: string
  description?: string
  tone: ToastTone
  durationMs: number
  dedupeKey?: string
}

type ToastInput = {
  title: string
  description?: string
  tone?: ToastTone
  durationMs?: number
  dedupeKey?: string
}

type ToastStoreState = {
  toasts: ToastEntry[]
  queue: ToastEntry[]
  pushToast: (toast: ToastInput) => number
  dismissToast: (id: number) => void
  clearToasts: () => void
}

let toastIdCounter = 0
let dismissTimerId: number | null = null

function clearDismissTimer() {
  if (dismissTimerId !== null) {
    window.clearTimeout(dismissTimerId)
    dismissTimerId = null
  }
}

export const useToastStore = create<ToastStoreState>((set, get) => ({
  toasts: [],
  queue: [],

  pushToast: (toast: ToastInput) => {
    const duration = toast.durationMs ?? 4000
    const dedupeKey = toast.dedupeKey?.trim()
    if (dedupeKey) {
      const { toasts, queue } = get()
      const duplicateExists = [...toasts, ...queue].some((entry) => entry.dedupeKey === dedupeKey)
      if (duplicateExists) {
        return -1
      }
    }

    toastIdCounter += 1
    const id = toastIdCounter
    const entry: ToastEntry = {
      id,
      title: toast.title,
      description: toast.description,
      tone: toast.tone ?? "info",
      durationMs: duration,
      dedupeKey,
    }

    const state = get()
    if (state.toasts.length === 0) {
      set({ toasts: [entry] })
      clearDismissTimer()
      dismissTimerId = window.setTimeout(() => {
        get().dismissToast(id)
      }, duration)
      return id
    }

    set((current) => ({ queue: [...current.queue, entry] }))
    return id
  },

  dismissToast: (id: number) => {
    const state = get()
    const activeToast = state.toasts[0]

    if (!activeToast || activeToast.id !== id) {
      set((current) => ({
        queue: current.queue.filter((toast) => toast.id !== id),
      }))
      return
    }

    clearDismissTimer()
    const [nextToast, ...remainingQueue] = state.queue
    if (!nextToast) {
      set({ toasts: [], queue: [] })
      return
    }

    set({ toasts: [nextToast], queue: remainingQueue })
    dismissTimerId = window.setTimeout(() => {
      get().dismissToast(nextToast.id)
    }, nextToast.durationMs)
  },

  clearToasts: () => {
    clearDismissTimer()
    set({ toasts: [], queue: [] })
  },
}))
