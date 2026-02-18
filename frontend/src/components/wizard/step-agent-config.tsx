import { useState } from "react"

import { AlertTriangle, Code2, Terminal } from "lucide-react"

import { type AgentChoice, type ApprovalMode, useWizardStore } from "@/stores/wizard-store"

const testPresets = [
  { label: "None", value: "" },
  { label: "pytest", value: "pytest -x -q --timeout=30" },
  { label: "npm test", value: "npm test" },
  { label: "Custom", value: "__custom__" },
]

const modelPresets: Record<AgentChoice, { label: string; value: string; description: string }[]> = {
  codex: [
    { label: "Default", value: "", description: "Agent default model" },
    { label: "o3", value: "o3", description: "Strongest reasoning" },
    { label: "o4-mini", value: "o4-mini", description: "Fast and affordable" },
    { label: "gpt-4.1", value: "gpt-4.1", description: "Balanced performance" },
    { label: "Custom", value: "__custom__", description: "Enter model name" },
  ],
  "claude-code": [
    { label: "Default", value: "", description: "Agent default model" },
    { label: "Opus", value: "opus", description: "Strongest reasoning" },
    { label: "Sonnet", value: "sonnet", description: "Fast and capable" },
    { label: "Custom", value: "__custom__", description: "Enter model name" },
  ],
}

const agents: { id: AgentChoice; name: string; description: string; icon: typeof Code2 }[] = [
  {
    id: "claude-code",
    name: "Claude Code",
    description: "Anthropic's coding agent with deep reasoning",
    icon: Code2,
  },
  {
    id: "codex",
    name: "Codex",
    description: "OpenAI's code generation CLI",
    icon: Terminal,
  },
]

export function StepAgentConfig() {
  const cli = useWizardStore((s) => s.cli)
  const setCli = useWizardStore((s) => s.setCli)
  const autoApproval = useWizardStore((s) => s.autoApproval)
  const setAutoApproval = useWizardStore((s) => s.setAutoApproval)
  const maxIterations = useWizardStore((s) => s.maxIterations)
  const setMaxIterations = useWizardStore((s) => s.setMaxIterations)
  const testCommand = useWizardStore((s) => s.testCommand)
  const setTestCommand = useWizardStore((s) => s.setTestCommand)
  const modelOverride = useWizardStore((s) => s.modelOverride)
  const setModelOverride = useWizardStore((s) => s.setModelOverride)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Agent Configuration</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose which AI coding agent will build your project and configure the loop settings.
        </p>
      </div>

      {/* Agent Selection */}
      <div className="space-y-3">
        <label className="block text-sm font-medium">AI Coding Agent</label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {agents.map((agent) => {
            const Icon = agent.icon
            const isSelected = cli === agent.id
            return (
              <button
                key={agent.id}
                type="button"
                onClick={() => setCli(agent.id)}
                className={`flex items-start gap-3 rounded-xl border-2 p-4 text-left transition-all ${
                  isSelected
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-input hover:border-muted-foreground/40 hover:bg-accent/30"
                }`}
              >
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                    isSelected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium">{agent.name}</p>
                  <p className="text-xs text-muted-foreground">{agent.description}</p>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Approval Mode */}
      <div className="space-y-3">
        <label className="block text-sm font-medium">Approval Mode</label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(["sandboxed", "full-auto"] as ApprovalMode[]).map((mode) => {
            const isSelected = autoApproval === mode
            return (
              <button
                key={mode}
                type="button"
                onClick={() => setAutoApproval(mode)}
                className={`rounded-xl border-2 p-4 text-left transition-all ${
                  isSelected
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-input hover:border-muted-foreground/40 hover:bg-accent/30"
                }`}
              >
                <p className="text-sm font-medium capitalize">{mode === "full-auto" ? "Full Auto" : "Sandboxed"}</p>
                <p className="text-xs text-muted-foreground">
                  {mode === "sandboxed"
                    ? "Safer — agent runs in sandboxed mode with restrictions"
                    : "Agent has full system access with no approval needed"}
                </p>
              </button>
            )
          })}
        </div>
        {autoApproval === "full-auto" && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
            <p className="text-xs text-amber-700 dark:text-amber-300">
              Full auto mode gives the agent unrestricted system access. Only use this in isolated environments.
            </p>
          </div>
        )}
      </div>

      {/* Max Iterations */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">
          Max Iterations: <span className="font-mono text-primary">{maxIterations}</span>
        </label>
        <input
          type="range"
          min={1}
          max={100}
          value={maxIterations}
          onChange={(e) => setMaxIterations(Number(e.target.value))}
          className="w-full accent-primary"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>1</span>
          <span>100</span>
        </div>
      </div>

      {/* Test Command */}
      <TestCommandField value={testCommand} onChange={setTestCommand} />

      {/* Model Override */}
      <ModelOverrideField cli={cli} value={modelOverride} onChange={setModelOverride} />
    </div>
  )
}

function ModelOverrideField({
  cli,
  value,
  onChange,
}: {
  cli: AgentChoice
  value: string
  onChange: (v: string) => void
}) {
  const presets = modelPresets[cli] ?? []
  const isPreset = presets.some((p) => p.value !== "__custom__" && p.value === value)
  const [isCustom, setIsCustom] = useState(!isPreset && value !== "")

  const activeValue = isCustom ? "__custom__" : presets.find((p) => p.value === value)?.value ?? "__custom__"

  // Reset custom state when agent changes and value was cleared
  const [prevCli, setPrevCli] = useState(cli)
  if (cli !== prevCli) {
    setPrevCli(cli)
    if (isCustom) setIsCustom(false)
  }

  const handleClick = (preset: (typeof presets)[number]) => {
    if (preset.value === "__custom__") {
      setIsCustom(true)
      if (isPreset) onChange("")
    } else {
      setIsCustom(false)
      onChange(preset.value)
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">
        Model
        <span className="ml-1 font-normal text-muted-foreground">(optional)</span>
      </label>
      <div className="flex flex-wrap gap-2">
        {presets.map((preset) => {
          const isActive = activeValue === preset.value
          return (
            <button
              key={preset.label}
              type="button"
              onClick={() => handleClick(preset)}
              className={`rounded-lg border px-3 py-1.5 text-left transition-all ${
                isActive
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-input text-muted-foreground hover:border-muted-foreground/40 hover:bg-accent/30"
              }`}
            >
              <span className="text-xs font-medium">{preset.label}</span>
              {preset.label !== "Default" && preset.label !== "Custom" && (
                <span className="ml-1.5 text-xs opacity-60">— {preset.description}</span>
              )}
            </button>
          )
        })}
      </div>
      {isCustom && (
        <input
          className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={cli === "codex" ? "e.g. o3-pro" : "e.g. claude-sonnet-4-5-20250929"}
          autoFocus
        />
      )}
    </div>
  )
}

function TestCommandField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const isPreset = testPresets.some((p) => p.value !== "__custom__" && p.value === value)
  const [isCustom, setIsCustom] = useState(!isPreset && value !== "")

  const activePreset = isCustom
    ? "__custom__"
    : testPresets.find((p) => p.value === value)?.value ?? "__custom__"

  const handlePresetClick = (preset: (typeof testPresets)[number]) => {
    if (preset.value === "__custom__") {
      setIsCustom(true)
      if (isPreset) onChange("")
    } else {
      setIsCustom(false)
      onChange(preset.value)
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">
        Test Command
        <span className="ml-1 font-normal text-muted-foreground">(optional)</span>
      </label>
      <div className="flex flex-wrap gap-2">
        {testPresets.map((preset) => {
          const isActive = activePreset === preset.value
          return (
            <button
              key={preset.label}
              type="button"
              onClick={() => handlePresetClick(preset)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                isActive
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-input text-muted-foreground hover:border-muted-foreground/40 hover:bg-accent/30"
              }`}
            >
              {preset.label}
            </button>
          )
        })}
      </div>
      {isCustom && (
        <input
          className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. cargo test, go test ./..."
          autoFocus
        />
      )}
      {!isCustom && value && (
        <div className="rounded-md border border-dashed border-input bg-muted/30 px-3 py-2">
          <code className="text-xs text-muted-foreground">{value}</code>
        </div>
      )}
    </div>
  )
}
