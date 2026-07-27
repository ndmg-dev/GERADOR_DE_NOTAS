import { create } from 'zustand'
import type { DadosExtraidos } from '@/types'

export type Step = 1 | 2 | 3

interface GerarNotasState {
  step: Step
  jobId: string | null
  balancoPdf: File | null
  drePdf: File | null
  empresaId: string
  ano: number
  dataAprovacao: string
  dados: DadosExtraidos | null
  nomeArquivoBaixado: string | null

  setStep: (step: Step) => void
  setJobId: (jobId: string) => void
  setBalancoPdf: (arquivo: File | null) => void
  setDrePdf: (arquivo: File | null) => void
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
  setEmpresaId: (empresaId) => set({ empresaId }),
  setAno: (ano) => set({ ano }),
  setDataAprovacao: (dataAprovacao) => set({ dataAprovacao }),
  setDados: (dados) => set({ dados }),
  setNomeArquivoBaixado: (nomeArquivoBaixado) => set({ nomeArquivoBaixado }),
  reset: () => set(estadoInicial),
}))
