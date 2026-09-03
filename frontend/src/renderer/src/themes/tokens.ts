export type ThemeName = 'cyberpunk' | 'premium' | 'modern'

export const THEME_LABELS: Record<ThemeName, string> = {
  cyberpunk: 'Cyberpunk',
  premium: 'Platin',
  modern: 'Modern'
}

/**
 * Each theme is a flat set of CSS custom properties applied on
 * documentElement via [data-theme]. Cyberpunk gets the deepest visual
 * treatment (HUD grid, scanline sweep, targeting rings — see global.css
 * [data-theme='cyberpunk'] rules) since it's the primary Jarvis-style look;
 * premium/modern are calmer variants sharing the same structure.
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
  premium: {
    '--bg': '#0c0b09',
    '--bg-elevated': '#151310',
    '--panel': 'rgba(28, 24, 18, 0.65)',
    '--panel-border': 'rgba(212, 175, 122, 0.28)',
    '--accent': '#d4af7a',
    '--accent-soft': 'rgba(212, 175, 122, 0.28)',
    '--accent-2': '#f5e6c8',
    '--text': '#f3ede2',
    '--text-dim': '#a89a86',
    '--font': "'New York', ui-serif, Georgia, 'Iowan Old Style', serif",
    '--orb-glow': '0 0 50px rgba(212, 175, 122, 0.45), 0 0 120px rgba(245, 230, 200, 0.15)',
    '--radius': '26px'
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
