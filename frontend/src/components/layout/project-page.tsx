import { useParams } from "react-router-dom"

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <section className="rounded-xl border bg-card p-6">
      <h1 className="text-xl font-semibold">Project: {id}</h1>
      <p className="mt-2 text-sm text-muted-foreground">Project detail tabs will be implemented in later phases.</p>
    </section>
  )
}
