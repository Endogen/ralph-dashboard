import { create } from "zustand"

export type ToastTone = "success" | "error" | "info"

export type ToastEntry = {
  id: number
  title: string
  description?: string
  tone: ToastTone
}

type ToastInput = {
  title: string
  description?: string
  tone?: ToastTone
  durationMs?: number
}

type ToastStoreState = {
  toasts: ToastEntry[]
  pushToast: (toast: ToastInput) => number
  dismissToast: (id: number) => void
  clearToasts: () => void
}

let toastIdCounter = 0

export const useToastStore = create<ToastStoreState>((set, get) => ({
  toasts: [],

  pushToast: (toast: ToastInput) => {
    toastIdCounter += 1
    const id = toastIdCounter
    const duration = toast.durationMs ?? 4000
    const entry: ToastEntry = {
      id,
      title: toast.title,
      description: toast.description,
      tone: toast.tone ?? "info",
    }

    set((state) => ({ toasts: [...state.toasts, entry] }))
    window.setTimeout(() => {
      get().dismissToast(id)
    }, duration)
    return id
  },

  dismissToast: (id: number) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),

  clearToasts: () => set({ toasts: [] }),
}))
