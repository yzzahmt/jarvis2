import { useState, type FormEvent } from 'react'
import { useJarvisStore } from '../../state/jarvisStore'

interface Props {
  onSend: (text: string) => void
}

export function TextInputBar({ onSend }: Props): JSX.Element {
  const [value, setValue] = useState('')
  const state = useJarvisStore((s) => s.state)

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const text = value.trim()
    if (!text || state !== 'idle') return
    onSend(text)
    setValue('')
  }

  return (
    <form className="text-input-bar" onSubmit={submit}>
      <input
        type="text"
        placeholder="Jarvis'e yaz..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={state !== 'idle'}
      />
      <button type="submit" disabled={state !== 'idle'}>
        Gönder
      </button>
    </form>
  )
}
