import { create } from 'zustand'
import type { AppState, JarvisSettings, ServerMessage, WakeSource } from '../ws/messages'

export type HandPoint = { x: number; y: number }

export interface TranscriptEntry {
  id: string
  role: 'user' | 'assistant'
  text: string
  ts: number
}

interface JarvisStore {
  connected: boolean
  state: AppState
  audioLevel: number
  lastWakeSource: WakeSource | null
  transcript: TranscriptEntry[]
  settings: JarvisSettings | null
  activeTool: { tool: string; args: Record<string, unknown> } | null
  lastError: { code: string; message: string } | null
  settingsOpen: boolean
  gestureActive: boolean
  gestureHands: HandPoint[][]

  setConnected: (connected: boolean) => void
  setSettingsOpen: (open: boolean) => void
  handleServerMessage: (msg: ServerMessage) => void
}

export const useJarvisStore = create<JarvisStore>((set) => ({
  connected: false,
  state: 'idle',
  audioLevel: 0,
  lastWakeSource: null,
  transcript: [],
  settings: null,
  activeTool: null,
  lastError: null,
  settingsOpen: false,
  gestureActive: false,
  gestureHands: [],

  setConnected: (connected) => set({ connected }),
  setSettingsOpen: (open) => set({ settingsOpen: open }),

  handleServerMessage: (msg) =>
    set((s) => {
      switch (msg.type) {
        case 'state_changed':
          return { state: msg.payload.state }
        case 'wake_triggered':
          return { lastWakeSource: msg.payload.source }
        case 'audio_level':
          return { audioLevel: msg.payload.rms }
        case 'transcript_final':
          return {
            transcript: [
              ...s.transcript,
              { id: msg.id, role: 'user', text: msg.payload.text, ts: msg.ts }
            ]
          }
        case 'assistant_reply':
          return {
            transcript: [
              ...s.transcript,
              { id: msg.id, role: 'assistant', text: msg.payload.text, ts: msg.ts }
            ],
            activeTool: null
          }
        case 'tool_call_started':
          return { activeTool: { tool: msg.payload.tool, args: msg.payload.args } }
        case 'tool_call_result':
          return { activeTool: null }
        case 'settings_state':
          return { settings: msg.payload.settings }
        case 'error':
          return { lastError: msg.payload }
        case 'gesture_state':
          return { gestureActive: msg.payload.active, gestureHands: [] }
        case 'gesture_landmarks':
          return { gestureHands: msg.payload.hands }
        default:
          return {}
      }
    })
}))
