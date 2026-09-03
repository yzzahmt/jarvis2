export type ThemeName = 'cyberpunk' | 'apple' | 'modern'

export const THEME_LABELS: Record<ThemeName, string> = {
  cyberpunk: 'Cyberpunk',
  apple: 'Apple',
  modern: 'Modern'
}

/**
 * Each theme is a flat set of CSS custom properties applied on
 * documentElement via [data-theme]. Cyberpunk gets the deepest visual
 * treatment (glow, scanlines) since it's the primary Jarvis-style look;
 * apple/modern are deliberately calmer variants sharing the same structure.
 */
export const THEME_VARS: Record<ThemeName, Record<string, string>> = {
  cyberpunk: {
    '--bg': '#05070d',
    '--bg-elevated': '#0a0f1a',
    '--panel': 'rgba(12, 18, 32, 0.72)',
    '--panel-border': 'rgba(0, 229, 255, 0.25)',
    '--accent': '#00e5ff',
    '--accent-soft': 'rgba(0, 229, 255, 0.35)',
    '--accent-2': '#ff2e88',
    '--text': '#e8fbff',
    '--text-dim': '#8fb4c0',
    '--font': "'SF Mono', 'JetBrains Mono', ui-monospace, monospace",
    '--orb-glow': '0 0 60px rgba(0, 229, 255, 0.55), 0 0 140px rgba(255, 46, 136, 0.25)',
    '--radius': '18px'
  },
  apple: {
    '--bg': '#f5f5f7',
    '--bg-elevated': '#ffffff',
    '--panel': 'rgba(255, 255, 255, 0.75)',
    '--panel-border': 'rgba(0, 0, 0, 0.08)',
    '--accent': '#0a84ff',
    '--accent-soft': 'rgba(10, 132, 255, 0.25)',
    '--accent-2': '#5e5ce6',
    '--text': '#1d1d1f',
    '--text-dim': '#6e6e73',
    '--font':
      "-apple-system, BlinkMacSystemFont, 'SF Pro Text', ui-sans-serif, system-ui, sans-serif",
    '--orb-glow': '0 0 40px rgba(10, 132, 255, 0.35)',
    '--radius': '22px'
  },
  modern: {
    '--bg': '#111318',
    '--bg-elevated': '#171a21',
    '--panel': 'rgba(255, 255, 255, 0.04)',
    '--panel-border': 'rgba(255, 255, 255, 0.10)',
    '--accent': '#7c5cff',
    '--accent-soft': 'rgba(124, 92, 255, 0.30)',
    '--accent-2': '#22d3ee',
    '--text': '#f2f2f5',
    '--text-dim': '#9a9aa5',
    '--font': "'Inter', ui-sans-serif, system-ui, sans-serif",
    '--orb-glow': '0 0 50px rgba(124, 92, 255, 0.4)',
    '--radius': '16px'
  }
}

export function applyTheme(name: ThemeName): void {
  const root = document.documentElement
  root.setAttribute('data-theme', name)
  const vars = THEME_VARS[name]
  for (const [key, value] of Object.entries(vars)) {
    root.style.setProperty(key, value)
  }
}
