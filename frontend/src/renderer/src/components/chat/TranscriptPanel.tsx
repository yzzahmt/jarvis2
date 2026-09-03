import { useEffect, useRef } from 'react'
import { useJarvisStore } from '../../state/jarvisStore'

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
        <div className="tool-banner">→ {activeTool.tool} çalıştırılıyor…</div>
      )}
    </div>
  )
}
