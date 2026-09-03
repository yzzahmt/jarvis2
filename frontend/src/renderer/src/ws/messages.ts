export type AppState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error'
export type WakeSource = 'wake_word' | 'clap' | 'manual'

export interface JarvisSettings {
  version: number
  voice: {
    engine: 'piper' | 'elevenlabs'
    voice_id: string
    elevenlabs_api_key: string | null
    elevenlabs_voice_id: string
  }
  theme: 'cyberpunk' | 'apple' | 'modern'
  input_mode: 'voice' | 'text'
  wake_word: { enabled: boolean; keyword: string; sensitivity: number }
  clap_trigger: { enabled: boolean; claps_required: number; window_ms: number }
  stt: { engine: string; model: string; language: string }
  llm: {
    provider: 'ollama' | 'cloud'
    ollama_model: string
    ollama_host: string
    cloud_provider: 'gemini' | 'groq' | null
    cloud_api_key: string | null
    cloud_model: string | null
  }
  system: { confirm_before_open: boolean }
  devices: {
    windows_host: string | null
    windows_user: string | null
    windows_ssh_key_path: string | null
  }
}

export interface ServerEnvelope<T = unknown> {
  type: string
  id: string
  ts: number
  payload: T
}

export type ServerMessage =
  | ServerEnvelope<{ state: AppState }> & { type: 'state_changed' }
  | ServerEnvelope<{ source: WakeSource }> & { type: 'wake_triggered' }
  | ServerEnvelope<{ text: string; lang: string }> & { type: 'transcript_final' }
  | ServerEnvelope<{ text: string; used_tools: string[] }> & { type: 'assistant_reply' }
  | ServerEnvelope<{ tool: string; args: Record<string, unknown> }> & { type: 'tool_call_started' }
  | ServerEnvelope<{ tool: string; ok: boolean; result: string }> & { type: 'tool_call_result' }
  | ServerEnvelope<{ rms: number }> & { type: 'audio_level' }
  | ServerEnvelope<{ settings: JarvisSettings }> & { type: 'settings_state' }
  | ServerEnvelope<{ code: string; message: string }> & { type: 'error' }

export function clientEnvelope(type: string, payload: Record<string, unknown> = {}) {
  return { type, payload }
}
