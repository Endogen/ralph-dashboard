import { useEffect, useLayoutEffect, useRef } from "react"
import { liveEvents, type LiveEventListener } from "@/lib/live-events"

/** Keep one subscription per mount and invoke the latest committed handler. */
export function useLiveEvent(listener: LiveEventListener) {
  const listenerRef = useRef(listener)
  useLayoutEffect(() => { listenerRef.current = listener }, [listener])
  useEffect(() => liveEvents.subscribe((event) => listenerRef.current(event)), [])
}
