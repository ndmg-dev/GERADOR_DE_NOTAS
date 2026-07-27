import { create } from 'zustand'
import type { DadosExtraidos } from '@/types'

export type Step = 1 | 2 | 3

/** Índice do exercício anterior: 0 → ano-1, 1 → ano-2. */
export type IndiceAnterior = 0 | 1

export interface ExercicioAnteriorState {
  balancoPdf: File | null
  drePdf: File | null
}

interface GerarNotasState {
  step: Step
  jobId: string | null
  balancoPdf: File | null
  drePdf: File | null
  anteriores: [ExercicioAnteriorState, ExercicioAnteriorState]
  empresaId: string
  ano: number
  dataAprovacao: string
  dados: DadosExtraidos | null
  nomeArquivoBaixado: string | null

  setStep: (step: Step) => void
  setJobId: (jobId: string) => void
  setBalancoPdf: (arquivo: File | null) => void
  setDrePdf: (arquivo: File | null) => void
  setAnterior: (
    indice: IndiceAnterior,
    campo: 'balancoPdf' | 'drePdf',
    arquivo: File | null,
  ) => void
  setEmpresaId: (id: string) => void
  setAno: (ano: number) => void
  setDataAprovacao: (data: string) => void
  setDados: (dados: DadosExtraidos) => void
  setNomeArquivoBaixado: (nome: string) => void
  reset: () => void
}

const estadoInicial = {
  step: 1 as Step,
  jobId: null,
  balancoPdf: null,
  drePdf: null,
  anteriores: [
    { balancoPdf: null, drePdf: null },
    { balancoPdf: null, drePdf: null },
  ] as [ExercicioAnteriorState, ExercicioAnteriorState],
  empresaId: '',
  ano: new Date().getFullYear() - 1,
  dataAprovacao: '',
  dados: null,
  nomeArquivoBaixado: null,
}

export const useGerarNotasStore = create<GerarNotasState>((set) => ({
  ...estadoInicial,

  setStep: (step) => set({ step }),
  setJobId: (jobId) => set({ jobId }),
  setBalancoPdf: (balancoPdf) => set({ balancoPdf }),
  setDrePdf: (drePdf) => set({ drePdf }),
  setAnterior: (indice, campo, arquivo) =>
    set((estado) => {
      const anteriores: [ExercicioAnteriorState, ExercicioAnteriorState] = [
        { ...estado.anteriores[0] },
        { ...estado.anteriores[1] },
      ]
      anteriores[indice][campo] = arquivo
      return { anteriores }
    }),
  setEmpresaId: (empresaId) => set({ empresaId }),
  setAno: (ano) => set({ ano }),
  setDataAprovacao: (dataAprovacao) => set({ dataAprovacao }),
  setDados: (dados) => set({ dados }),
  setNomeArquivoBaixado: (nomeArquivoBaixado) => set({ nomeArquivoBaixado }),
  reset: () => set(estadoInicial),
}))
