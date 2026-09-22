import { apiFetch } from "@/api/client"
import { useWizardStore, type GeneratedFile } from "@/stores/wizard-store"
import { deliverAttentionSignal } from "@/lib/native-notifications"

let polling = false
/** Survives route changes; the request ID survives a full browser reload. */
export function ensureGenerationPolling() {
  if (polling || !useWizardStore.getState().activeGenerationRequestId) return
  polling = true
  const poll = async () => {
    const id = useWizardStore.getState().activeGenerationRequestId
    if (!id) { polling = false; return }
    try {
      const result = await apiFetch<{ status: string; files: GeneratedFile[] | null; error: string | null }>(
        `/wizard/generate/status/${encodeURIComponent(id)}`)
      if (id !== useWizardStore.getState().activeGenerationRequestId) return
      if (result.status !== "pending") {
        useWizardStore.setState({ isGenerating: false, activeGenerationRequestId: null,
          generationStartedAt: null, generateError: result.error,
          ...(result.files ? { generatedFiles: result.files } : {}) })
        void deliverAttentionSignal({ title: result.error ? "Generation failed" : "Plan ready for review",
          description: result.error ?? `${result.files?.length ?? 0} files generated`,
          tone: result.error ? "error" : "success", dedupeKey: `generation:${id}` })
      }
    } catch (err) {
      if (id !== useWizardStore.getState().activeGenerationRequestId) return
      const message = err instanceof Error ? err.message : "Connection lost; retrying"
      if (message.includes("(404)")) {
        useWizardStore.setState({ isGenerating: false, activeGenerationRequestId: null,
          generationStartedAt: null, generateError: "This generation is no longer available. Generate again." })
      } else {
        useWizardStore.setState({ generateError: "Connection interrupted. Reconnecting to your generation…" })
      }
    } finally {
      if (useWizardStore.getState().activeGenerationRequestId) window.setTimeout(() => void poll(), 2000)
      else polling = false
    }
  }
  void poll()
}
