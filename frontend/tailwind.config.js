/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Fundo quase preto, com tom quente — base da identidade Mendonça Galvão.
        fundo: '#0f0c09',
        'fundo-alt': '#0a0806',
        // Superfícies elevadas (cards, tabelas, diálogos).
        superficie: '#17120d',
        'superficie-alt': '#1e1811',
        borda: '#2a2119',
        'borda-clara': '#3d3124',
        // Dourado de destaque.
        ouro: {
          DEFAULT: '#c9a961',
          claro: '#e2cd93',
          escuro: '#a1823f',
          tenue: 'rgba(201, 169, 97, 0.12)',
        },
        // Tipografia.
        texto: '#f2ece1',
        'texto-suave': '#a89a86',
        'texto-fraco': '#6f6558',
        // Estados.
        sucesso: '#4ade80',
        erro: '#f87171',
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        cartao: '0 1px 2px rgba(0, 0, 0, 0.4)',
        destaque: '0 0 0 1px rgba(201, 169, 97, 0.35)',
      },
    },
  },
  plugins: [],
}
