import { type MutableRefObject, useCallback, useEffect, useMemo, useRef, useState } from "react"

import { useAuthStore } from "@/stores/auth-store"

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000] as const

export type WebSocketEnvelope = {
  type: string
  project?: string
  timestamp?: string
  data?: unknown
  message?: string
}

type UseWebSocketOptions = {
  enabled?: boolean
  projects?: string[]
  onEvent?: (event: WebSocketEnvelope) => void
}

type UseWebSocketResult = {
  socketRef: MutableRefObject<WebSocket | null>
  connected: boolean
  reconnecting: boolean
  sendJson: (payload: Record<string, unknown>) => boolean
}

function normalizeProjects(projects: string[] | undefined): string[] {
  if (!projects) {
    return []
  }
  return Array.from(new Set(projects.map((item) => item.trim()).filter(Boolean))).sort()
}

function buildWebSocketUrl(accessToken: string): string {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws"
  const host = window.location.host
  return `${protocol}://${host}/api/ws?token=${encodeURIComponent(accessToken)}`
}

export function useWebSocket({
  enabled = true,
  projects = [],
  onEvent,
}: UseWebSocketOptions = {}): UseWebSocketResult {
  const accessToken = useAuthStore((state) => state.accessToken)
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)
  const reconnectAttemptRef = useRef(0)
  const projectsRef = useRef<string[]>(normalizeProjects(projects))
  const subscribedProjectsRef = useRef<string[]>([])
  const onEventRef = useRef(onEvent)

  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)

  const normalizedProjects = useMemo(() => normalizeProjects(projects), [projects])
  projectsRef.current = normalizedProjects
  onEventRef.current = onEvent

  const sendJson = useCallback((payload: Record<string, unknown>) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false
    }
    socket.send(JSON.stringify(payload))
    return true
  }, [])

  useEffect(() => {
    if (!enabled || !accessToken) {
      setConnected(false)
      setReconnecting(false)
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
      return
    }

    let cancelled = false

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
    }

    const connect = () => {
      if (cancelled) {
        return
      }

      const socket = new WebSocket(buildWebSocketUrl(accessToken))
      socketRef.current = socket

      socket.onopen = () => {
        if (cancelled) {
          return
        }
        clearReconnectTimer()
        reconnectAttemptRef.current = 0
        setConnected(true)
        setReconnecting(false)

        if (projectsRef.current.length > 0) {
          socket.send(JSON.stringify({ action: "subscribe", projects: projectsRef.current }))
          subscribedProjectsRef.current = projectsRef.current
        } else {
          subscribedProjectsRef.current = []
        }
      }

      socket.onmessage = (event: MessageEvent<string>) => {
        if (!onEventRef.current) {
          return
        }
        try {
          const parsed = JSON.parse(event.data) as WebSocketEnvelope
          onEventRef.current(parsed)
        } catch {
          // Ignore malformed websocket messages and keep the stream alive.
        }
      }

      socket.onerror = () => {
        socket.close()
      }

      socket.onclose = () => {
        setConnected(false)
        if (cancelled) {
          return
        }

        setReconnecting(true)
        const delay =
          RECONNECT_DELAYS_MS[Math.min(reconnectAttemptRef.current, RECONNECT_DELAYS_MS.length - 1)]
        reconnectAttemptRef.current += 1
        reconnectTimerRef.current = window.setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      cancelled = true
      setConnected(false)
      setReconnecting(false)
      clearReconnectTimer()
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
    }
  }, [accessToken, enabled])

  useEffect(() => {
    if (!connected) {
      return
    }

    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return
    }

    const previous = new Set(subscribedProjectsRef.current)
    const next = new Set(normalizedProjects)

    const toSubscribe = normalizedProjects.filter((project) => !previous.has(project))
    const toUnsubscribe = subscribedProjectsRef.current.filter((project) => !next.has(project))

    if (toSubscribe.length > 0) {
      socket.send(JSON.stringify({ action: "subscribe", projects: toSubscribe }))
    }
    if (toUnsubscribe.length > 0) {
      socket.send(JSON.stringify({ action: "unsubscribe", projects: toUnsubscribe }))
    }
    subscribedProjectsRef.current = normalizedProjects
  }, [connected, normalizedProjects])

  return { socketRef, connected, reconnecting, sendJson }
}
