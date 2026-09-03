import type { JarvisSettings } from '../../ws/messages'
import { THEME_LABELS, type ThemeName } from '../../themes/tokens'

const VOICE_OPTIONS = [
  { id: 'en_US-lessac-medium', label: 'Lessac (EN-US)' },
  { id: 'en_US-amy-medium', label: 'Amy (EN-US)' },
  { id: 'en_GB-alan-medium', label: 'Alan (EN-GB)' },
  { id: 'tr_TR-dfki-medium', label: 'Dfki (TR, erkek)' }
]

interface Props {
  settings: JarvisSettings
  onChange: (partial: Record<string, unknown>) => void
  onClose: () => void
}

export function SettingsPanel({ settings, onChange, onClose }: Props): JSX.Element {
  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <h2>Ayarlar</h2>

        <div className="settings-row">
          <label>Tema</label>
          <div className="segmented">
            {(Object.keys(THEME_LABELS) as ThemeName[]).map((t) => (
              <button
                key={t}
                className={settings.theme === t ? 'active' : ''}
                onClick={() => onChange({ theme: t })}
              >
                {THEME_LABELS[t]}
              </button>
            ))}
          </div>
        </div>

        <div className="settings-row">
          <label>Giriş modu</label>
          <div className="segmented">
            <button
              className={settings.input_mode === 'voice' ? 'active' : ''}
              onClick={() => onChange({ input_mode: 'voice' })}
            >
              Sesli
            </button>
            <button
              className={settings.input_mode === 'text' ? 'active' : ''}
              onClick={() => onChange({ input_mode: 'text' })}
            >
              Yazılı
            </button>
          </div>
        </div>

        <div className="settings-row">
          <label>Ses motoru</label>
          <div className="segmented">
            <button
              className={settings.voice.engine === 'piper' ? 'active' : ''}
              onClick={() => onChange({ voice: { engine: 'piper' } })}
            >
              Yerel (Piper)
            </button>
            <button
              className={settings.voice.engine === 'elevenlabs' ? 'active' : ''}
              onClick={() => onChange({ voice: { engine: 'elevenlabs' } })}
            >
              Bulut (ElevenLabs, kadın TR)
            </button>
          </div>
        </div>

        {settings.voice.engine === 'piper' ? (
          <div className="settings-row">
            <label>Ses (TTS)</label>
            <select
              value={settings.voice.voice_id}
              onChange={(e) => onChange({ voice: { voice_id: e.target.value } })}
            >
              {VOICE_OPTIONS.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="settings-row">
            <label>ElevenLabs API anahtarı</label>
            <input
              type="password"
              defaultValue={settings.voice.elevenlabs_api_key ?? ''}
              placeholder="elevenlabs.io API anahtarını yapıştır"
              onBlur={(e) => onChange({ voice: { elevenlabs_api_key: e.target.value } })}
            />
          </div>
        )}

        <div className="settings-row">
          <label>"Hey Jarvis" ile uyanma</label>
          <div className="segmented">
            <button
              className={settings.wake_word.enabled ? 'active' : ''}
              onClick={() => onChange({ wake_word: { enabled: true } })}
            >
              Açık
            </button>
            <button
              className={!settings.wake_word.enabled ? 'active' : ''}
              onClick={() => onChange({ wake_word: { enabled: false } })}
            >
              Kapalı
            </button>
          </div>
        </div>

        <div className="settings-row">
          <label>Alkışla uyanma</label>
          <div className="segmented">
            <button
              className={settings.clap_trigger.enabled ? 'active' : ''}
              onClick={() => onChange({ clap_trigger: { enabled: true } })}
            >
              Açık
            </button>
            <button
              className={!settings.clap_trigger.enabled ? 'active' : ''}
              onClick={() => onChange({ clap_trigger: { enabled: false } })}
            >
              Kapalı
            </button>
          </div>
        </div>

        <div className="settings-row">
          <label>AI beyni</label>
          <div className="segmented">
            <button
              className={settings.llm.provider === 'ollama' ? 'active' : ''}
              onClick={() => onChange({ llm: { provider: 'ollama' } })}
            >
              Yerel (Ollama)
            </button>
            <button
              className={settings.llm.provider === 'cloud' ? 'active' : ''}
              onClick={() => onChange({ llm: { provider: 'cloud' } })}
            >
              Bulut
            </button>
          </div>
        </div>

        {settings.llm.provider === 'ollama' ? (
          <div className="settings-row">
            <label>Ollama modeli</label>
            <input
              type="text"
              defaultValue={settings.llm.ollama_model}
              onBlur={(e) => onChange({ llm: { ollama_model: e.target.value } })}
            />
          </div>
        ) : (
          <>
            <div className="settings-row">
              <label>Bulut sağlayıcı</label>
              <select
                value={settings.llm.cloud_provider ?? 'groq'}
                onChange={(e) => onChange({ llm: { cloud_provider: e.target.value } })}
              >
                <option value="groq">Groq (ücretsiz katman)</option>
                <option value="gemini">Google Gemini (ücretsiz katman)</option>
              </select>
            </div>
            <div className="settings-row">
              <label>API anahtarı</label>
              <input
                type="password"
                defaultValue={settings.llm.cloud_api_key ?? ''}
                placeholder="ücretsiz API anahtarını yapıştır"
                onBlur={(e) => onChange({ llm: { cloud_api_key: e.target.value } })}
              />
            </div>
          </>
        )}

        <button className="settings-close" onClick={onClose}>
          Kapat
        </button>
      </div>
    </div>
  )
}
