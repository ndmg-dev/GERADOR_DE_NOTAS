import { FileText, Upload, X } from 'lucide-react'
import { useCallback } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'

interface UploadZoneProps {
  titulo: string
  descricao: string
  arquivo: File | null
  onArquivoSelecionado: (arquivo: File | null) => void
  onErro?: (mensagem: string) => void
}

const TAMANHO_MAXIMO = 50 * 1024 * 1024

export function UploadZone({
  titulo,
  descricao,
  arquivo,
  onArquivoSelecionado,
  onErro,
}: UploadZoneProps) {
  const onDrop = useCallback(
    (aceitos: File[], rejeitados: FileRejection[]) => {
      if (rejeitados.length > 0) {
        const motivo = rejeitados[0]?.errors[0]?.code
        onErro?.(
          motivo === 'file-too-large'
            ? 'O arquivo excede o limite de 50 MB.'
            : 'Somente arquivos .pdf são aceitos.',
        )
        return
      }
      const selecionado = aceitos[0]
      if (selecionado) onArquivoSelecionado(selecionado)
    },
    [onArquivoSelecionado, onErro],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: TAMANHO_MAXIMO,
    multiple: false,
  })

  if (arquivo) {
    return (
      <div className="rounded-lg border border-neutral-300 bg-neutral-50 p-6">
        <p className="text-sm font-semibold text-neutral-900">{titulo}</p>
        <div className="mt-4 flex items-center gap-3 rounded-md border border-neutral-200 bg-white p-3">
          <FileText className="h-5 w-5 shrink-0 text-neutral-600" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm text-neutral-900">{arquivo.name}</p>
            <p className="text-xs text-neutral-500">
              {(arquivo.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <button
            type="button"
            onClick={() => onArquivoSelecionado(null)}
            aria-label={`Remover ${titulo}`}
            className="rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      {...getRootProps()}
      className={`cursor-pointer rounded-lg border-2 border-dashed p-6 transition-colors ${
        isDragActive
          ? 'border-neutral-900 bg-neutral-100'
          : 'border-neutral-300 bg-white hover:border-neutral-400'
      }`}
    >
      <input {...getInputProps()} />
      <p className="text-sm font-semibold text-neutral-900">{titulo}</p>
      <div className="mt-6 flex flex-col items-center gap-2 text-center">
        <Upload className="h-8 w-8 text-neutral-400" />
        <p className="text-sm text-neutral-600">
          {isDragActive ? 'Solte o arquivo aqui' : 'Arraste o PDF ou clique para selecionar'}
        </p>
        <p className="text-xs text-neutral-500">{descricao}</p>
      </div>
    </div>
  )
}
