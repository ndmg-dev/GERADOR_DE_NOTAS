import * as ToastPrimitive from '@radix-ui/react-toast'
import { CheckCircle2, X, XCircle } from 'lucide-react'
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

type Variante = 'sucesso' | 'erro'

interface ToastMensagem {
  id: number
  titulo: string
  descricao?: string
  variante: Variante
}

interface ToastContextValue {
  notificar: (titulo: string, opcoes?: { descricao?: string; variante?: Variante }) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const contexto = useContext(ToastContext)
  if (!contexto) throw new Error('useToast precisa estar dentro de <ToastProvider>')
  return contexto
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [mensagens, setMensagens] = useState<ToastMensagem[]>([])

  const notificar = useCallback<ToastContextValue['notificar']>((titulo, opcoes) => {
    setMensagens((atuais) => [
      ...atuais,
      {
        id: Date.now() + Math.random(),
        titulo,
        descricao: opcoes?.descricao,
        variante: opcoes?.variante ?? 'sucesso',
      },
    ])
  }, [])

  const valor = useMemo(() => ({ notificar }), [notificar])

  return (
    <ToastContext.Provider value={valor}>
      <ToastPrimitive.Provider swipeDirection="right" duration={6000}>
        {children}

        {mensagens.map((mensagem) => (
          <ToastPrimitive.Root
            key={mensagem.id}
            onOpenChange={(aberto) => {
              if (!aberto) {
                setMensagens((atuais) => atuais.filter((m) => m.id !== mensagem.id))
              }
            }}
            className="flex items-start gap-3 rounded-md border border-borda bg-superficie-alt p-4 shadow-lg"
          >
            {mensagem.variante === 'sucesso' ? (
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-ouro" />
            ) : (
              <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-erro" />
            )}
            <div className="flex-1">
              <ToastPrimitive.Title className="text-sm font-semibold text-texto">
                {mensagem.titulo}
              </ToastPrimitive.Title>
              {mensagem.descricao && (
                <ToastPrimitive.Description className="mt-1 text-sm text-texto-suave">
                  {mensagem.descricao}
                </ToastPrimitive.Description>
              )}
            </div>
            <ToastPrimitive.Close
              aria-label="Fechar"
              className="text-texto-fraco transition-colors hover:text-texto"
            >
              <X className="h-4 w-4" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}

        <ToastPrimitive.Viewport className="fixed bottom-0 right-0 z-50 flex w-96 max-w-full flex-col gap-2 p-4" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}
