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

const campoClasse = 'campo'

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
          <label className="rotulo">
            Razão social *
          </label>
          <input
            {...register('nome', { required: 'Informe a razão social' })}
            className={campoClasse}
          />
          {errors.nome && (
            <p className="mt-1 text-xs text-erro">{errors.nome.message}</p>
          )}
        </div>

        <div>
          <label className="rotulo">CNPJ *</label>
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
            <p className="mt-1 text-xs text-erro">{errors.cnpj.message}</p>
          )}
        </div>

        <div>
          <label className="rotulo">Endereço</label>
          <input {...register('endereco')} className={campoClasse} />
        </div>
      </div>

      <fieldset className="rounded-lg border border-borda p-4">
        <legend className="px-1 text-sm font-semibold text-texto">Contador</legend>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="rotulo">Nome</label>
            <input {...register('contador_nome')} className={campoClasse} />
          </div>
          <div>
            <label className="rotulo">CRC</label>
            <input {...register('contador_crc')} className={campoClasse} />
          </div>
          <div>
            <label className="rotulo">CPF</label>
            <input {...register('contador_cpf')} className={campoClasse} />
          </div>
        </div>
      </fieldset>

      <fieldset className="rounded-lg border border-borda p-4">
        <legend className="px-1 text-sm font-semibold text-texto">
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
                className="rounded border border-borda px-2 text-texto-fraco transition-colors hover:border-erro/40 hover:text-erro"
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
            className="btn-neutro px-3 py-1.5"
          >
            <Plus className="h-4 w-4" /> Adicionar sócio
          </button>
        </div>
      </fieldset>

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="btn-neutro"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={salvando}
          className="btn-ouro"
        >
          {salvando ? 'Salvando...' : 'Salvar'}
        </button>
      </div>
    </form>
  )
}
