import { useEffect, useRef } from 'react'
import { useJarvisStore } from '../../state/jarvisStore'

const TOOL_LABELS: Record<string, string> = {
  compare_prices: 'Fiyatlar taranıyor…',
  add_to_cart: 'Sepete ekleniyor…',
  youtube_open: 'Video başlatılıyor…',
  web_search: 'Web araştırılıyor…',
  open_app: 'Uygulama açılıyor…',
  open_developer_console: 'Konsol açılıyor…',
  get_current_datetime: 'Saat kontrol ediliyor…',
  get_system_info: 'Sistem bilgisi alınıyor…'
}

export function TranscriptPanel(): JSX.Element {
  const transcript = useJarvisStore((s) => s.transcript)
  const activeTool = useJarvisStore((s) => s.activeTool)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: 'smooth' })
  }, [transcript, activeTool])

  return (
    <div className="transcript-panel" ref={ref}>
      {transcript.map((entry) => (
        <div key={entry.id} className={`transcript-entry ${entry.role}`}>
          <div className="transcript-role">{entry.role === 'user' ? 'Sen' : 'Jarvis'}</div>
          {entry.text}
        </div>
      ))}
      {activeTool && (
        <div className="tool-banner">→ {TOOL_LABELS[activeTool.tool] ?? `${activeTool.tool} çalıştırılıyor…`}</div>
      )}
    </div>
  )
}
