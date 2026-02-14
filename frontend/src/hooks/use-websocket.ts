import { useEffect, useRef } from "react"

export function useWebSocket(url: string, enabled = true) {
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!enabled) {
      return
    }

    const socket = new WebSocket(url)
    socketRef.current = socket

    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [enabled, url])

  return socketRef
}
