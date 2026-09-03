import { useEffect, useRef } from 'react'
import { useJarvisStore } from '../../state/jarvisStore'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  r: number
}

const PARTICLE_COUNT = 70
const LINK_DIST = 130

export function AnimatedBackground(): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const audioLevelRef = useRef(0)
  const audioLevel = useJarvisStore((s) => s.audioLevel)

  useEffect(() => {
    audioLevelRef.current = audioLevel
  }, [audioLevel])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let width = 0
    let height = 0

    const resize = (): void => {
      width = canvas.clientWidth
      height = canvas.clientHeight
      canvas.width = width * devicePixelRatio
      canvas.height = height * devicePixelRatio
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    particlesRef.current = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      r: Math.random() * 1.6 + 0.6
    }))

    const styles = getComputedStyle(document.documentElement)

    const tick = (): void => {
      const accent = styles.getPropertyValue('--accent').trim() || '#00e5ff'
      const accent2 = styles.getPropertyValue('--accent-2').trim() || accent
      ctx.clearRect(0, 0, width, height)

      const pulse = 1 + Math.min(audioLevelRef.current * 4, 1.2)
      const particles = particlesRef.current

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        p.x += p.vx * pulse
        p.y += p.vy * pulse
        if (p.x < 0 || p.x > width) p.vx *= -1
        if (p.y < 0 || p.y > height) p.vy *= -1

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r * pulse, 0, Math.PI * 2)
        ctx.fillStyle = accent
        ctx.globalAlpha = 0.55
        ctx.fill()

        for (let j = i + 1; j < particles.length; j++) {
          const q = particles[j]
          const dx = p.x - q.x
          const dy = p.y - q.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < LINK_DIST) {
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(q.x, q.y)
            ctx.strokeStyle = accent2
            ctx.globalAlpha = 0.14 * (1 - dist / LINK_DIST)
            ctx.lineWidth = 1
            ctx.stroke()
          }
        }
      }
      ctx.globalAlpha = 1
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={canvasRef} className="animated-bg" />
}
