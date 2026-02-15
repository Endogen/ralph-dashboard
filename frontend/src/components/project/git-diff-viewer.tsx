type GitDiffViewerProps = {
  commitHash: string
  diff: string | null
  isLoading: boolean
  error: string | null
}

function diffLineClass(line: string): string {
  if (line.startsWith("@@")) {
    return "text-violet-300"
  }
  if (line.startsWith("diff --git") || line.startsWith("index ") || line.startsWith("---") || line.startsWith("+++")) {
    return "text-sky-300"
  }
  if (line.startsWith("+") && !line.startsWith("+++")) {
    return "bg-emerald-500/10 text-emerald-200"
  }
  if (line.startsWith("-") && !line.startsWith("---")) {
    return "bg-rose-500/10 text-rose-200"
  }
  return "text-zinc-100"
}

export function GitDiffViewer({ commitHash, diff, isLoading, error }: GitDiffViewerProps) {
  const normalizedDiff = diff?.trim() ?? ""

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-100">
      <div className="mb-2 text-[11px] text-zinc-300">Commit {commitHash} diff</div>

      {isLoading ? (
        <p className="text-zinc-400">Loading diff...</p>
      ) : error ? (
        <p className="text-rose-300">{error}</p>
      ) : normalizedDiff.length === 0 ? (
        <p className="text-zinc-400">No diff available for this commit.</p>
      ) : (
        <pre className="max-h-[320px] overflow-auto whitespace-pre-wrap break-all pr-2 text-[11px] leading-5">
          {normalizedDiff.split("\n").map((line, index) => (
            <span key={`${commitHash}-${index}`} className={`block ${diffLineClass(line)}`}>
              {line}
            </span>
          ))}
        </pre>
      )}
    </div>
  )
}
