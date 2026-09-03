import { useJarvisStore } from '../../state/jarvisStore'
import { TextInputBar } from '../chat/TextInputBar'

interface Props {
  onPushToTalkStart: () => void
  onPushToTalkStop: () => void
  onTextSend: (text: string) => void
  onGestureToggle: () => void
}

export function Dock({
  onPushToTalkStart,
  onPushToTalkStop,
  onTextSend,
  onGestureToggle
}: Props): JSX.Element {
  const settings = useJarvisStore((s) => s.settings)
  const state = useJarvisStore((s) => s.state)
  const gestureActive = useJarvisStore((s) => s.gestureActive)
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
      <button
        className={`gesture-button ${gestureActive ? 'active' : ''}`}
        onClick={onGestureToggle}
        title="El hareketiyle fare kontrolü"
      >
        🖐 {gestureActive ? 'El kontrolü açık' : 'El kontrolü'}
      </button>
      <TextInputBar onSend={onTextSend} />
    </div>
  )
}
