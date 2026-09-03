import { useJarvisStore } from '../../state/jarvisStore'
import { TextInputBar } from '../chat/TextInputBar'

interface Props {
  onPushToTalkStart: () => void
  onPushToTalkStop: () => void
  onTextSend: (text: string) => void
}

export function Dock({ onPushToTalkStart, onPushToTalkStop, onTextSend }: Props): JSX.Element {
  const settings = useJarvisStore((s) => s.settings)
  const state = useJarvisStore((s) => s.state)
  const isListening = state === 'listening'

  return (
    <div className="dock">
      <button
        className={`talk-button ${isListening ? 'active' : ''}`}
        onClick={() => (isListening ? onPushToTalkStop() : onPushToTalkStart())}
        disabled={state === 'thinking' || state === 'speaking'}
      >
        {isListening ? 'Dinliyor... (durdurmak için tıkla)' : 'Konuşmak için tıkla'}
      </button>
      <TextInputBar onSend={onTextSend} />
    </div>
  )
}
