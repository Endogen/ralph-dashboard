import { useCallback, useEffect, useMemo, useState } from "react"

import { apiFetch } from "@/api/client"
import { useToastStore } from "@/stores/toast-store"
import type { LoopConfig } from "@/types/project"

type ProjectConfigPanelProps = {
  projectId?: string
  projectPath?: string | null
}

type PricingRow = {
  id: string
  model: string
  price: string
}

const CLI_OPTIONS = ["codex", "claude"] as const
type CliOption = (typeof CLI_OPTIONS)[number]
const FORM_CONTROL_CLASS =
  "h-10 w-full rounded-md border border-input bg-background px-3 text-sm leading-5 text-foreground"
const READ_ONLY_FORM_CONTROL_CLASS =
  "h-10 w-full rounded-md border border-input bg-muted/40 px-3 text-sm leading-5 text-muted-foreground"
let pricingRowCounter = 0

function nextPricingRowId(): string {
  pricingRowCounter += 1
  return `pricing-${pricingRowCounter}`
}

function cloneConfig(config: LoopConfig): LoopConfig {
  return {
    cli: config.cli,
    flags: config.flags,
    max_iterations: config.max_iterations,
    test_command: config.test_command,
    model_pricing: { ...config.model_pricing },
  }
}

function normalizeCli(value: string): CliOption {
  if (CLI_OPTIONS.includes(value as CliOption)) {
    return value as CliOption
  }
  return "codex"
}

function formatPrice(value: number): string {
  if (!Number.isFinite(value)) {
    return ""
  }
  const normalized = value.toFixed(6).replace(/\.?0+$/, "")
  return normalized.length > 0 ? normalized : "0"
}

function pricingRowsFromConfig(config: LoopConfig): PricingRow[] {
  return Object.entries(config.model_pricing)
    .sort(([leftModel], [rightModel]) => leftModel.localeCompare(rightModel))
    .map(([model, price]) => ({
      id: nextPricingRowId(),
      model,
      price: formatPrice(price),
    }))
}

function serializeConfig(config: LoopConfig): string {
  const normalizedPricing = Object.fromEntries(
    Object.entries(config.model_pricing)
      .sort(([leftModel], [rightModel]) => leftModel.localeCompare(rightModel))
      .map(([model, price]) => [model, Number(price)]),
  )

  return JSON.stringify({
    cli: config.cli,
    flags: config.flags,
    max_iterations: config.max_iterations,
    test_command: config.test_command,
    model_pricing: normalizedPricing,
  })
}

export function ProjectConfigPanel({ projectId, projectPath }: ProjectConfigPanelProps) {
  const [cli, setCli] = useState("codex")
  const [flags, setFlags] = useState("")
  const [maxIterations, setMaxIterations] = useState("20")
  const [testCommand, setTestCommand] = useState("")
  const [pricingRows, setPricingRows] = useState<PricingRow[]>([])
  const [savedConfig, setSavedConfig] = useState<LoopConfig | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
  const pushToast = useToastStore((state) => state.pushToast)

  const applyConfig = useCallback((config: LoopConfig) => {
    const nextConfig = cloneConfig(config)
    const normalizedCli = normalizeCli(nextConfig.cli)
    const normalizedConfig: LoopConfig = {
      ...nextConfig,
      cli: normalizedCli,
    }
    setCli(normalizedCli)
    setFlags(nextConfig.flags)
    setMaxIterations(String(nextConfig.max_iterations))
    setTestCommand(nextConfig.test_command)
    setPricingRows(pricingRowsFromConfig(nextConfig))
    setSavedConfig(normalizedConfig)
  }, [])

  useEffect(() => {
    let cancelled = false

    const loadConfig = async () => {
      if (!projectId) {
        setCli("codex")
        setFlags("")
        setMaxIterations("20")
        setTestCommand("")
        setPricingRows([])
        setSavedConfig(null)
        setLoadError(null)
        setFormError(null)
        setSaveMessage(null)
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      setLoadError(null)
      setFormError(null)
      setSaveMessage(null)
      try {
        const response = await apiFetch<LoopConfig>(`/projects/${projectId}/config`)
        if (cancelled) {
          return
        }
        applyConfig(response)
      } catch (error) {
        if (cancelled) {
          return
        }
        const message = error instanceof Error ? error.message : "Failed to load project config"
        setLoadError(message)
        setSavedConfig(null)
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadConfig()

    return () => {
      cancelled = true
    }
  }, [applyConfig, projectId])

  const buildPayload = useCallback((): LoopConfig => {
    const normalizedCli = cli.trim()
    if (!normalizedCli) {
      throw new Error("CLI is required.")
    }

    const parsedMaxIterations = Number.parseInt(maxIterations.trim(), 10)
    if (!Number.isFinite(parsedMaxIterations) || parsedMaxIterations < 0) {
      throw new Error("Max iterations must be 0 or greater (0 means unlimited).")
    }

    const modelPricing: Record<string, number> = {}
    for (const [index, row] of pricingRows.entries()) {
      const model = row.model.trim()
      const priceText = row.price.trim()

      if (!model && !priceText) {
        continue
      }
      if (!model) {
        throw new Error(`Model pricing row ${index + 1} is missing a model name.`)
      }
      if (!priceText) {
        throw new Error(`Model pricing row ${index + 1} is missing a price.`)
      }

      const numericPrice = Number(priceText)
      if (!Number.isFinite(numericPrice) || numericPrice < 0) {
        throw new Error(`Model pricing row ${index + 1} must have a non-negative number.`)
      }
      if (modelPricing[model] !== undefined) {
        throw new Error(`Duplicate model pricing entry: ${model}.`)
      }
      modelPricing[model] = numericPrice
    }

    return {
      cli: normalizedCli,
      flags: flags.trim(),
      max_iterations: parsedMaxIterations,
      test_command: testCommand.trim(),
      model_pricing: modelPricing,
    }
  }, [cli, flags, maxIterations, pricingRows, testCommand])

  const cliOptions = useMemo(() => [...CLI_OPTIONS], [])

  const isDirty = useMemo(() => {
    if (!savedConfig) {
      return false
    }
    try {
      return serializeConfig(buildPayload()) !== serializeConfig(savedConfig)
    } catch {
      return true
    }
  }, [buildPayload, savedConfig])

  const handleCopyProjectPath = useCallback(async () => {
    if (!projectPath) {
      return
    }
    if (!navigator.clipboard?.writeText) {
      setCopyMessage("Clipboard is unavailable.")
      pushToast({
        title: "Copy unavailable",
        description: "Clipboard API is not available in this browser.",
        tone: "error",
      })
      return
    }

    try {
      await navigator.clipboard.writeText(projectPath)
      setCopyMessage("Copied.")
      pushToast({
        title: "Project path copied",
        tone: "success",
      })
    } catch {
      setCopyMessage("Failed to copy.")
      pushToast({
        title: "Copy failed",
        tone: "error",
      })
    }
  }, [projectPath, pushToast])

  const updatePricingRow = useCallback((rowId: string, field: "model" | "price", value: string) => {
    setPricingRows((current) =>
      current.map((row) =>
        row.id === rowId
          ? {
              ...row,
              [field]: value,
            }
          : row,
      ),
    )
  }, [])

  const addPricingRow = useCallback(() => {
    setPricingRows((current) => [
      ...current,
      {
        id: nextPricingRowId(),
        model: "",
        price: "",
      },
    ])
  }, [])

  const removePricingRow = useCallback((rowId: string) => {
    setPricingRows((current) => current.filter((row) => row.id !== rowId))
  }, [])

  const handleSaveConfig = useCallback(async () => {
    if (!projectId) {
      return
    }

    setIsSaving(true)
    setFormError(null)
    setSaveMessage(null)
    try {
      const payload = buildPayload()
      const saved = await apiFetch<LoopConfig>(`/projects/${projectId}/config`, {
        method: "PUT",
        body: JSON.stringify(payload),
      })
      applyConfig(saved)
      setSaveMessage("Saved .ralph/config.json")
      pushToast({
        title: "Config saved",
        description: ".ralph/config.json updated",
        tone: "success",
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save config"
      setFormError(message)
      pushToast({
        title: "Config save failed",
        description: message,
        tone: "error",
      })
    } finally {
      setIsSaving(false)
    }
  }, [applyConfig, buildPayload, projectId, pushToast])

  return (
    <section className="rounded-xl p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Config</h3>
        <p className="text-sm text-muted-foreground">
          Configure loop runtime values that are persisted to `.ralph/config.json`.
        </p>
      </header>

      {isLoading ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-muted-foreground">
          Loading project config...
        </div>
      ) : loadError ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-rose-600 dark:text-rose-400">
          {loadError}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">CLI</span>
              <select
                value={cli}
                onChange={(event) => setCli(event.target.value)}
                className={`${FORM_CONTROL_CLASS} pr-8`}
              >
                {cliOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Max Iterations
              </span>
              <input
                type="number"
                min={0}
                value={maxIterations}
                onChange={(event) => setMaxIterations(event.target.value)}
                className={FORM_CONTROL_CLASS}
              />
              <p className="text-xs text-muted-foreground">Set to 0 for unlimited iterations.</p>
            </label>

            <label className="space-y-1 lg:col-span-2">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">CLI Flags</span>
              <input
                value={flags}
                onChange={(event) => setFlags(event.target.value)}
                placeholder="-s workspace-write"
                className={FORM_CONTROL_CLASS}
              />
            </label>

            <label className="space-y-1 lg:col-span-2">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Test Command
              </span>
              <input
                value={testCommand}
                onChange={(event) => setTestCommand(event.target.value)}
                placeholder="cd backend && .venv/bin/pytest --timeout=30 -x"
                className={FORM_CONTROL_CLASS}
              />
            </label>

            <div className="space-y-1 lg:col-span-2">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Project Directory
              </span>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={projectPath ?? ""}
                  className={READ_ONLY_FORM_CONTROL_CLASS}
                />
                <button
                  type="button"
                  onClick={handleCopyProjectPath}
                  disabled={!projectPath}
                  className="rounded-md border bg-background px-3 py-2 text-xs font-medium hover:bg-background/80 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Copy
                </button>
              </div>
              {copyMessage && <p className="text-xs text-muted-foreground">{copyMessage}</p>}
            </div>
          </div>

          <article className="rounded-lg border bg-background/30 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <h4 className="text-sm font-semibold">Model Pricing (USD per 1K tokens)</h4>
              <button
                type="button"
                onClick={addPricingRow}
                disabled={isSaving}
                className="rounded-md border bg-background px-2 py-1 text-xs font-medium hover:bg-background/80 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Add Model
              </button>
            </div>

            {pricingRows.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No pricing overrides set. Add rows to customize token cost calculations.
              </p>
            ) : (
              <div className="space-y-2">
                {pricingRows.map((row, index) => (
                  <div key={row.id} className="grid grid-cols-[minmax(0,1fr)_140px_auto] gap-2">
                    <input
                      value={row.model}
                      onChange={(event) => updatePricingRow(row.id, "model", event.target.value)}
                      placeholder={`model-${index + 1}`}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground"
                    />
                    <input
                      value={row.price}
                      onChange={(event) => updatePricingRow(row.id, "price", event.target.value)}
                      placeholder="0.006"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground"
                    />
                    <button
                      type="button"
                      onClick={() => removePricingRow(row.id)}
                      disabled={isSaving}
                      className="rounded-md border bg-background px-2 py-2 text-xs font-medium hover:bg-background/80 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </article>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              Config updates are applied on the next loop start unless the loop script hot-reloads settings.
            </p>
            <button
              type="button"
              onClick={handleSaveConfig}
              disabled={!projectId || isSaving || !isDirty}
              className="rounded-md border bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? "Saving..." : "Save Config"}
            </button>
          </div>

          {formError && <p className="text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
          {saveMessage && <p className="text-sm text-emerald-600 dark:text-emerald-400">{saveMessage}</p>}
        </div>
      )}
    </section>
  )
}
