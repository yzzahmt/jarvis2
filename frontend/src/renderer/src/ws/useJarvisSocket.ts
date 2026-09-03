import { useEffect, useRef, useCallback } from 'react'
import { useJarvisStore } from '../state/jarvisStore'
import { clientEnvelope, type ServerMessage } from './messages'

const WS_URL = 'ws://127.0.0.1:8756/ws'
const RECONNECT_DELAY_MS = 1500

export function useJarvisSocket() {
  const socketRef = useRef<WebSocket | null>(null)
  const handleServerMessage = useJarvisStore((s) => s.handleServerMessage)
  const setConnected = useJarvisStore((s) => s.setConnected)

  useEffect(() => {
    let cancelled = false
    let reconnectTimer: ReturnType<typeof setTimeout>

    const connect = () => {
      if (cancelled) return
      const ws = new WebSocket(WS_URL)
      socketRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        ws.send(JSON.stringify(clientEnvelope('settings_get')))
      }
      ws.onclose = () => {
        setConnected(false)
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as ServerMessage
          handleServerMessage(msg)
        } catch {
          // ignore malformed frames
        }
      }
    }

    connect()
    return () => {
      cancelled = true
      clearTimeout(reconnectTimer)
      socketRef.current?.close()
    }
  }, [handleServerMessage, setConnected])

  const send = useCallback((type: string, payload: Record<string, unknown> = {}) => {
    const ws = socketRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(clientEnvelope(type, payload)))
    }
  }, [])

  return { send }
}
