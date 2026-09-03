import { motion } from 'framer-motion'
import { useJarvisStore } from '../../state/jarvisStore'

const STATE_LABEL: Record<string, string> = {
  idle: 'Hazır',
  listening: 'Dinliyorum',
  thinking: 'Düşünüyorum',
  speaking: 'Konuşuyorum',
  error: 'Hata'
}

const RING_COUNT = 3

export function JarvisOrb(): JSX.Element {
  const state = useJarvisStore((s) => s.state)
  const audioLevel = useJarvisStore((s) => s.audioLevel)

  const coreScale =
    state === 'listening' ? 1 + Math.min(audioLevel * 3, 0.35) : state === 'thinking' ? 1.05 : 1

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18 }}>
      <div style={{ position: 'relative', width: 220, height: 220 }}>
        <motion.div
          className="hud-ring"
          animate={{ rotate: 360 }}
          transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
          style={{ position: 'absolute', inset: -14 }}
        >
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="hud-tick"
              style={{ transform: `rotate(${i * 30}deg) translateY(-124px)` }}
            />
          ))}
        </motion.div>

        {Array.from({ length: RING_COUNT }).map((_, i) => (
          <motion.div
            key={i}
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: '50%',
              border: '1px solid var(--accent-soft)'
            }}
            animate={
              state === 'listening' || state === 'thinking'
                ? { scale: [1, 1.35 + i * 0.12, 1], opacity: [0.6, 0, 0.6] }
                : { scale: 1, opacity: 0.25 }
            }
            transition={{
              duration: 2.4 + i * 0.4,
              repeat: state === 'idle' || state === 'speaking' ? 0 : Infinity,
              ease: 'easeInOut',
              delay: i * 0.3
            }}
          />
        ))}

        <motion.div
          animate={{ scale: coreScale, rotate: state === 'thinking' ? 360 : 0 }}
          transition={
            state === 'thinking'
              ? { rotate: { duration: 3, repeat: Infinity, ease: 'linear' }, scale: { duration: 0.2 } }
              : { duration: 0.25 }
          }
          style={{
            position: 'absolute',
            inset: '30%',
            borderRadius: '50%',
            background:
              'radial-gradient(circle at 35% 30%, var(--accent) 0%, var(--accent-2) 65%, transparent 100%)',
            boxShadow: 'var(--orb-glow)'
          }}
        />

        {state === 'speaking' && (
          <motion.div
            animate={{ scale: [1, 1.12, 1] }}
            transition={{ duration: 0.9, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              position: 'absolute',
              inset: '30%',
              borderRadius: '50%',
              border: '2px solid var(--accent)'
            }}
          />
        )}
      </div>

      <div className="state-label">{STATE_LABEL[state] ?? state}</div>
      <div className="hud-readout">
        LVL {audioLevel.toFixed(2)} · SYS.{state.toUpperCase()}
      </div>
    </div>
  )
}
