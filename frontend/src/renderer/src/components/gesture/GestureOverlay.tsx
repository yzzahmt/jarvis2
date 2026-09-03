import { useEffect, useRef } from 'react'
import { useJarvisStore } from '../../state/jarvisStore'

// Standard 21-point Mediapipe hand skeleton connections.
const HAND_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], // thumb
  [0, 5], [5, 6], [6, 7], [7, 8], // index
  [5, 9], [9, 10], [10, 11], [11, 12], // middle
  [9, 13], [13, 14], [14, 15], [15, 16], // ring
  [13, 17], [17, 18], [18, 19], [19, 20], // pinky
  [0, 17] // palm base
]

export function GestureOverlay(): JSX.Element | null {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const gestureActive = useJarvisStore((s) => s.gestureActive)
  const gestureHands = useJarvisStore((s) => s.gestureHands)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * devicePixelRatio
    canvas.height = height * devicePixelRatio
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
    ctx.clearRect(0, 0, width, height)

    const styles = getComputedStyle(document.documentElement)
    const accent = styles.getPropertyValue('--accent').trim() || '#00e5ff'
    const accent2 = styles.getPropertyValue('--accent-2').trim() || accent

    gestureHands.forEach((points, handIdx) => {
      const color = handIdx === 0 ? accent : accent2

      ctx.strokeStyle = color
      ctx.lineWidth = 2.5
      ctx.shadowColor = color
      ctx.shadowBlur = 8
      for (const [a, b] of HAND_CONNECTIONS) {
        const pa = points[a]
        const pb = points[b]
        if (!pa || !pb) continue
        ctx.beginPath()
        ctx.moveTo(pa.x * width, pa.y * height)
        ctx.lineTo(pb.x * width, pb.y * height)
        ctx.stroke()
      }

      ctx.fillStyle = color
      for (const p of points) {
        ctx.beginPath()
        ctx.arc(p.x * width, p.y * height, 3.5, 0, Math.PI * 2)
        ctx.fill()
      }
    })
  }, [gestureHands])

  if (!gestureActive) return null

  return <canvas ref={canvasRef} className="gesture-overlay" />
}
