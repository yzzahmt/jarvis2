import { useEffect } from 'react'
import { useJarvisSocket } from './ws/useJarvisSocket'
import { useJarvisStore } from './state/jarvisStore'
import { applyTheme, type ThemeName } from './themes/tokens'
import { JarvisOrb } from './components/orb/JarvisOrb'
import { TranscriptPanel } from './components/chat/TranscriptPanel'
import { Dock } from './components/layout/Dock'
import { SettingsPanel } from './components/settings/SettingsPanel'

function App(): JSX.Element {
  const { send } = useJarvisSocket()
  const connected = useJarvisStore((s) => s.connected)
  const settings = useJarvisStore((s) => s.settings)
  const settingsOpen = useJarvisStore((s) => s.settingsOpen)
  const setSettingsOpen = useJarvisStore((s) => s.setSettingsOpen)
  const lastError = useJarvisStore((s) => s.lastError)

  useEffect(() => {
    if (settings?.theme) applyTheme(settings.theme as ThemeName)
  }, [settings?.theme])

  return (
    <div className="app-shell">
      <div className="stage">
        <button className="settings-trigger no-drag" onClick={() => setSettingsOpen(true)}>
          ⚙
        </button>
        <div className="status-pill">
          <span className={`status-dot ${connected ? 'connected' : ''}`} />
          {connected ? 'Bağlı' : 'Bağlanıyor…'}
        </div>

        <JarvisOrb />
        <TranscriptPanel />

        {lastError && <div className="error-toast">{lastError.message}</div>}
      </div>

      <Dock
        onPushToTalkStart={() => send('push_to_talk_start')}
        onPushToTalkStop={() => send('push_to_talk_stop')}
        onTextSend={(text) => send('text_input', { text })}
      />

      {settingsOpen && settings && (
        <SettingsPanel
          settings={settings}
          onChange={(partial) => send('settings_set', { settings: partial })}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </div>
  )
}

export default App
