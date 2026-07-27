import { FileText } from 'lucide-react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { Dashboard } from '@/pages/Dashboard'
import { Empresas } from '@/pages/Empresas'
import { GerarNotas } from '@/pages/GerarNotas'
import { Historico } from '@/pages/Historico'

const LINKS = [
  { para: '/', rotulo: 'Visão geral' },
  { para: '/gerar', rotulo: 'Gerar Notas' },
  { para: '/historico', rotulo: 'Histórico' },
  { para: '/empresas', rotulo: 'Empresas' },
]

export function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-borda bg-fundo-alt/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-md border border-ouro/30 bg-ouro-tenue">
              <FileText className="h-4 w-4 text-ouro" />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold text-texto">Notas Explicativas</p>
              <p className="text-xs text-texto-fraco">Mendonça Galvão</p>
            </div>
          </div>

          <nav className="flex gap-1">
            {LINKS.map((link) => (
              <NavLink
                key={link.para}
                to={link.para}
                end={link.para === '/'}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm transition-colors ${
                    isActive
                      ? 'border border-ouro/30 bg-ouro-tenue text-ouro'
                      : 'border border-transparent text-texto-suave hover:bg-superficie hover:text-texto'
                  }`
                }
              >
                {link.rotulo}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/gerar" element={<GerarNotas />} />
          <Route path="/historico" element={<Historico />} />
          <Route path="/empresas" element={<Empresas />} />
        </Routes>
      </main>

      <footer className="mx-auto max-w-6xl px-6 pb-8">
        <p className="text-xs text-texto-fraco">
          Gerador de Notas Explicativas — uso interno
        </p>
      </footer>
    </div>
  )
}
