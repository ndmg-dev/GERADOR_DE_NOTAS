import { Plus, Trash2 } from 'lucide-react'
import { useFieldArray, useForm } from 'react-hook-form'
import type { Empresa, EmpresaPayload } from '@/types'

interface EmpresaFormProps {
  empresa?: Empresa | null
  onSubmit: (payload: EmpresaPayload) => void
  onCancel: () => void
  salvando: boolean
}

function valoresIniciais(empresa?: Empresa | null): EmpresaPayload {
  return {
    nome: empresa?.nome ?? '',
    cnpj: empresa?.cnpj ?? '',
    endereco: empresa?.endereco ?? '',
    socios: empresa?.socios ?? [],
    contador_nome: empresa?.contador_nome ?? '',
    contador_crc: empresa?.contador_crc ?? '',
    contador_cpf: empresa?.contador_cpf ?? '',
  }
}

const campoClasse =
  'w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-900 focus:outline-none'

export function EmpresaForm({ empresa, onSubmit, onCancel, salvando }: EmpresaFormProps) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<EmpresaPayload>({ defaultValues: valoresIniciais(empresa) })

  const { fields, append, remove } = useFieldArray({ control, name: 'socios' })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="mb-1 block text-sm font-medium text-neutral-800">
            Razão social *
          </label>
          <input
            {...register('nome', { required: 'Informe a razão social' })}
            className={campoClasse}
          />
          {errors.nome && (
            <p className="mt-1 text-xs text-red-600">{errors.nome.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-800">CNPJ *</label>
          <input
            {...register('cnpj', {
              required: 'Informe o CNPJ',
              pattern: {
                value: /^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}$/,
                message: 'Use o formato 00.000.000/0000-00',
              },
            })}
            placeholder="00.000.000/0000-00"
            className={campoClasse}
          />
          {errors.cnpj && (
            <p className="mt-1 text-xs text-red-600">{errors.cnpj.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-800">Endereço</label>
          <input {...register('endereco')} className={campoClasse} />
        </div>
      </div>

      <fieldset className="rounded-lg border border-neutral-200 p-4">
        <legend className="px-1 text-sm font-semibold text-neutral-900">Contador</legend>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-sm text-neutral-700">Nome</label>
            <input {...register('contador_nome')} className={campoClasse} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-neutral-700">CRC</label>
            <input {...register('contador_crc')} className={campoClasse} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-neutral-700">CPF</label>
            <input {...register('contador_cpf')} className={campoClasse} />
          </div>
        </div>
      </fieldset>

      <fieldset className="rounded-lg border border-neutral-200 p-4">
        <legend className="px-1 text-sm font-semibold text-neutral-900">
          Quadro societário
        </legend>

        <div className="space-y-3">
          {fields.map((field, indice) => (
            <div key={field.id} className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr_1fr_auto]">
              <input
                {...register(`socios.${indice}.nome` as const)}
                placeholder="Nome"
                className={campoClasse}
              />
              <input
                {...register(`socios.${indice}.cpf` as const)}
                placeholder="CPF"
                className={campoClasse}
              />
              <input
                {...register(`socios.${indice}.participacao` as const)}
                placeholder="Participação"
                className={campoClasse}
              />
              <input
                {...register(`socios.${indice}.cargo` as const)}
                placeholder="Cargo"
                className={campoClasse}
              />
              <button
                type="button"
                onClick={() => remove(indice)}
                aria-label="Remover sócio"
                className="rounded border border-neutral-300 px-2 text-neutral-500 hover:bg-neutral-100 hover:text-red-600"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}

          <button
            type="button"
            onClick={() =>
              append({ nome: '', cpf: '', participacao: '', cargo: 'Sócio Administrador' })
            }
            className="inline-flex items-center gap-2 rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-100"
          >
            <Plus className="h-4 w-4" /> Adicionar sócio
          </button>
        </div>
      </fieldset>

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-neutral-300 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={salvando}
          className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {salvando ? 'Salvando...' : 'Salvar'}
        </button>
      </div>
    </form>
  )
}
