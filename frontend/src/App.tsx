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
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-6 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-neutral-900" />
            <span className="font-semibold text-neutral-900">Notas Explicativas</span>
          </div>

          <nav className="flex gap-1">
            {LINKS.map((link) => (
              <NavLink
                key={link.para}
                to={link.para}
                end={link.para === '/'}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 text-sm ${
                    isActive
                      ? 'bg-neutral-900 text-white'
                      : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
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
    </div>
  )
}
