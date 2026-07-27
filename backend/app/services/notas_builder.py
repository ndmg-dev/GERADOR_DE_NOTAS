"""Montagem da estrutura das Notas Explicativas a partir dos dados extraídos.

A estrutura segue o modelo de referência da Soberana: 20 notas, com tabelas
comparativas de até três exercícios lado a lado (exercício corrente primeiro).

Cada nota é um objeto :class:`Nota` com blocos ordenados de parágrafo e tabela.
Notas cujos grupos não existem no balanço (ex.: adiantamento de clientes
zerado) são automaticamente omitidas, e a numeração final é sequencial sobre
as notas que sobraram.

Os textos descritivos vêm de arquivos ``.txt`` em ``app/templates/notas/``,
permitindo que o time contábil os edite sem alterar código. Os parâmetros
dinâmicos usam a sintaxe ``{empresa.nome}``, ``{config.ano}`` etc.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "notas"

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][\w]*(?:\.[\w]+)*)\}")

MAX_EXERCICIOS = 3


def formatar_brl(valor: float | None, *, vazio: str = "0,00") -> str:
    """Formata 1566336.51 → '1.566.336,51'."""
    if valor is None:
        return vazio
    inteiro = f"{abs(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"-{inteiro}" if valor < 0 else inteiro


def positivo(valor: float | None) -> float | None:
    """Contas credoras vêm negativas do Domínio; as notas exibem o módulo."""
    return None if valor is None else abs(valor)


def _normalizar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento.upper()).strip()


_CONECTIVOS = {"a", "e", "o", "de", "da", "do", "das", "dos", "em", "no", "na", "ao"}
# Siglas que devem permanecer em caixa alta.
_SIGLAS = {
    "FGTS", "INSS", "IRPJ", "CSLL", "ISS", "PIS", "COFINS", "IRRF", "PCC",
    "ICMS", "IPI", "CPP", "RAT", "FAP", "PF", "PJ", "CC", "AG", "S/A",
}


def _titulo_legivel(descricao: str) -> str:
    """'DUPLICATAS A RECEBER' → 'Duplicatas a Receber'.

    Preserva siglas e capitaliza também depois de barras e hifens, para não
    produzir coisas como 'Adiantamento a Socios/titular'.
    """

    def capitalizar(palavra: str) -> str:
        if not palavra:
            return palavra
        # Trata separadores internos: SOCIOS/TITULAR, -PROF
        for separador in ("/", "-"):
            if separador in palavra:
                return separador.join(capitalizar(p) for p in palavra.split(separador))
        nucleo = palavra.strip("()")
        if nucleo.upper() in _SIGLAS:
            return palavra.replace(nucleo, nucleo.upper())
        return palavra.capitalize()

    palavras = descricao.strip().split()
    saida = []
    for indice, palavra in enumerate(palavras):
        if indice > 0 and palavra.lower() in _CONECTIVOS:
            saida.append(palavra.lower())
        else:
            saida.append(capitalizar(palavra.lower()))
    return " ".join(saida)


# --------------------------------------------------------------------------- #
# Estruturas
# --------------------------------------------------------------------------- #


@dataclass
class Paragrafo:
    texto: str
    tipo: Literal["paragrafo"] = "paragrafo"

    def to_dict(self) -> dict[str, Any]:
        return {"tipo": self.tipo, "texto": self.texto}


@dataclass
class Tabela:
    colunas: list[str]
    linhas: list[list[str]]
    total: list[str] | None = None
    titulo: str | None = None
    tipo: Literal["tabela"] = "tabela"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "titulo": self.titulo,
            "colunas": self.colunas,
            "linhas": self.linhas,
            "total": self.total,
        }


@dataclass
class Nota:
    numero: int
    titulo: str
    tipo: Literal["texto", "tabela", "misto"]
    conteudo: list[Paragrafo | Tabela] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "numero": self.numero,
            "titulo": self.titulo,
            "tipo": self.tipo,
            "conteudo": [bloco.to_dict() for bloco in self.conteudo],
        }


@dataclass
class Exercicio:
    """Um exercício social com seus demonstrativos já extraídos."""

    ano: int
    balanco: dict[str, Any] = field(default_factory=dict)
    dre: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> Exercicio:
        return cls(
            ano=int(dados.get("ano") or 0),
            balanco=dados.get("balanco") or {},
            dre=dados.get("dre") or {},
        )


# --------------------------------------------------------------------------- #
# Serviço
# --------------------------------------------------------------------------- #


class NotasBuilderService:
    """Recebe os dados do parser e monta a lista ordenada de notas."""

    TEMPLATES = {
        "contexto": "nota_01_contexto.txt",
        "apresentacao": "nota_02_apresentacao.txt",
        "praticas": "nota_03_praticas.txt",
        "caixa": "nota_04_caixa.txt",
        "clientes": "nota_05_clientes.txt",
        "creditos": "nota_06_creditos.txt",
        "realizavel_lp": "nota_07_realizavel_lp.txt",
        "imobilizado": "nota_08_imobilizado.txt",
        "fornecedores": "nota_09_fornecedores.txt",
        "emprestimos": "nota_10_emprestimos.txt",
        "obrigacoes_trabalhistas": "nota_11_obrigacoes_trabalhistas.txt",
        "obrigacoes_fiscais": "nota_12_obrigacoes_fiscais.txt",
        "adiantamento_clientes": "nota_13_adiantamento_clientes.txt",
        "outras_obrigacoes": "nota_14_outras_obrigacoes.txt",
        "provisoes": "nota_15_provisoes.txt",
        "capital_social": "nota_16_capital_social.txt",
        "receita": "nota_17_receita.txt",
        "natureza_despesas": "nota_18_natureza_despesas.txt",
        "resultado_financeiro": "nota_19_resultado_financeiro.txt",
        "aprovacao": "nota_20_aprovacao.txt",
    }

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._contexto: dict[str, Any] = {}
        self._exercicios: list[Exercicio] = []

    # ------------------------------------------------------------ Templates

    def _render(self, chave: str, **extra: Any) -> list[str]:
        caminho = self.templates_dir / self.TEMPLATES[chave]
        try:
            bruto = caminho.read_text(encoding="utf-8")
        except OSError:
            logger.warning("Template ausente: %s", caminho)
            return []

        contexto = {**self._contexto, **extra}

        def substituir(match: re.Match[str]) -> str:
            valor = self._resolver(match.group(1), contexto)
            return match.group(0) if valor is None else str(valor)

        texto = _PLACEHOLDER_RE.sub(substituir, bruto)
        return [p.strip() for p in texto.split("\n\n") if p.strip()]

    @staticmethod
    def _resolver(caminho: str, contexto: dict[str, Any]) -> Any:
        atual: Any = contexto
        for parte in caminho.split("."):
            if isinstance(atual, dict):
                if parte not in atual:
                    return None
                atual = atual[parte]
            else:
                atual = getattr(atual, parte, None)
                if atual is None:
                    return None
        return atual

    def _paragrafos(self, chave: str, **extra: Any) -> list[Paragrafo]:
        return [Paragrafo(texto=t) for t in self._render(chave, **extra)]

    # ---------------------------------------------------------------- Build

    def build_all(
        self,
        exercicios: list[dict[str, Any]] | list[Exercicio],
        empresa: dict[str, Any],
        config: dict[str, Any],
    ) -> list[Nota]:
        """Monta as notas a partir de um a três exercícios, do mais recente ao mais antigo."""
        self._exercicios = [
            e if isinstance(e, Exercicio) else Exercicio.from_dict(e)
            for e in exercicios
        ][:MAX_EXERCICIOS]

        if not self._exercicios:
            self._exercicios = [Exercicio(ano=int(config.get("ano") or 0))]

        self._contexto = {
            "empresa": empresa,
            "config": config,
            "ano": self._exercicios[0].ano,
            "anos": ", ".join(str(e.ano) for e in self._exercicios),
        }

        candidatas = [
            self.nota_contexto_operacional(empresa),
            self.nota_apresentacao(config),
            self.nota_praticas_contabeis(),
            self.nota_caixa(),
            self.nota_clientes(),
            self.nota_creditos(),
            self.nota_realizavel_lp(),
            self.nota_imobilizado(),
            self.nota_fornecedores(),
            self.nota_emprestimos(),
            self.nota_obrigacoes_trabalhistas(),
            self.nota_obrigacoes_fiscais(),
            self.nota_adiantamento_clientes(),
            self.nota_outras_obrigacoes(),
            self.nota_provisoes(),
            self.nota_capital_social(empresa),
            self.nota_receita(),
            self.nota_natureza_despesas(),
            self.nota_resultado_financeiro(),
            self.nota_aprovacao(empresa, config),
        ]

        notas = [n for n in candidatas if n is not None]
        for numero, nota in enumerate(notas, start=1):
            nota.numero = numero

        logger.info(
            "Notas montadas: %d de %d possíveis (%d exercício[s])",
            len(notas),
            len(candidatas),
            len(self._exercicios),
        )
        return notas

    # ------------------------------------------------------------ Auxiliares

    @property
    def _anos(self) -> list[str]:
        return [str(e.ano) for e in self._exercicios]

    @property
    def _atual(self) -> Exercicio:
        return self._exercicios[0]

    @staticmethod
    def _caminho(dados: dict[str, Any], *chaves: str) -> Any:
        atual: Any = dados
        for chave in chaves:
            if not isinstance(atual, dict):
                return None
            atual = atual.get(chave)
            if atual is None:
                return None
        return atual

    def _grupo_do_ano(
        self, exercicio: Exercicio, caminho: tuple[str, ...]
    ) -> dict[str, Any] | None:
        return self._caminho(exercicio.balanco, *caminho)

    def _tabela_comparativa(
        self,
        caminhos: tuple[tuple[str, ...], ...],
        *,
        rotulo_total: str = "Total",
        usar_modulo: bool = True,
    ) -> Tabela | None:
        """Monta uma tabela com uma coluna por exercício.

        ``caminhos`` permite reunir mais de um grupo do balanço na mesma nota
        (ex.: obrigações fiscais + parcelamentos).
        """
        # Ordem das linhas: primeira aparição no exercício mais recente.
        ordem: list[str] = []
        valores: dict[str, dict[int, float]] = {}
        rotulos: dict[str, str] = {}
        totais: dict[int, float] = {}
        encontrou = False

        for exercicio in self._exercicios:
            total_ano = 0.0
            tem_grupo = False

            for caminho in caminhos:
                grupo = self._grupo_do_ano(exercicio, caminho)
                if not grupo:
                    continue
                tem_grupo = True
                encontrou = True

                for item in grupo.get("itens", []):
                    chave = _normalizar(item["descricao"])
                    if chave not in valores:
                        valores[chave] = {}
                        rotulos[chave] = _titulo_legivel(item["descricao"])
                        ordem.append(chave)
                    valor = item["valor"]
                    valores[chave][exercicio.ano] = (
                        abs(valor) if usar_modulo else valor
                    )

                if grupo.get("total") is not None:
                    total_ano += (
                        abs(grupo["total"]) if usar_modulo else grupo["total"]
                    )

            if tem_grupo:
                totais[exercicio.ano] = round(total_ano, 2)

        if not encontrou:
            return None

        linhas = [
            [rotulos[chave]]
            + [
                formatar_brl(valores[chave].get(e.ano, 0.0))
                for e in self._exercicios
            ]
            for chave in ordem
        ]

        # Sem composição analítica: a única linha usa o nome do próprio grupo,
        # para não repetir "Total" duas vezes na tabela.
        if not linhas:
            grupo_atual = next(
                (
                    g
                    for g in (self._grupo_do_ano(self._atual, c) for c in caminhos)
                    if g
                ),
                None,
            )
            rotulo_linha = _titulo_legivel(
                (grupo_atual or {}).get("descricao") or rotulo_total
            )
            linhas = [
                [rotulo_linha]
                + [formatar_brl(totais.get(e.ano, 0.0)) for e in self._exercicios]
            ]

        return Tabela(
            colunas=["Descrição"] + self._anos,
            linhas=linhas,
            total=[rotulo_total]
            + [formatar_brl(totais.get(e.ano, 0.0)) for e in self._exercicios],
        )

    def _nota_de_grupo(
        self,
        chave_template: str,
        titulo: str,
        caminhos: tuple[tuple[str, ...], ...],
        *,
        rotulo_total: str = "Total",
    ) -> Nota | None:
        tabela = self._tabela_comparativa(caminhos, rotulo_total=rotulo_total)
        if tabela is None:
            return None

        total_atual = 0.0
        for caminho in caminhos:
            grupo = self._grupo_do_ano(self._atual, caminho)
            if grupo and grupo.get("total") is not None:
                total_atual += abs(grupo["total"])

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(chave_template, total=formatar_brl(total_atual))
        )
        conteudo.append(tabela)
        return Nota(numero=0, titulo=titulo, tipo="misto", conteudo=conteudo)

    # ---------------------------------------------------------------- Notas

    def nota_contexto_operacional(self, empresa: dict[str, Any]) -> Nota | None:
        return Nota(
            numero=0,
            titulo="Contexto operacional",
            tipo="texto",
            conteudo=list(self._paragrafos("contexto")),
        )

    def nota_apresentacao(self, config: dict[str, Any]) -> Nota | None:
        return Nota(
            numero=0,
            titulo="Apresentação das Demonstrações Contábeis",
            tipo="texto",
            conteudo=list(self._paragrafos("apresentacao")),
        )

    def nota_praticas_contabeis(self) -> Nota | None:
        return Nota(
            numero=0,
            titulo="Sumário das principais práticas contábeis",
            tipo="texto",
            conteudo=list(self._paragrafos("praticas")),
        )

    def nota_caixa(self) -> Nota | None:
        return self._nota_de_grupo(
            "caixa",
            "Caixa e equivalentes de Caixa",
            ((("ativo", "circulante", "caixa_equivalentes")),),
        )

    def nota_clientes(self) -> Nota | None:
        return self._nota_de_grupo(
            "clientes",
            "Contas a receber de clientes",
            ((("ativo", "circulante", "clientes")),),
        )

    def nota_creditos(self) -> Nota | None:
        return self._nota_de_grupo(
            "creditos",
            "Créditos",
            (
                ("ativo", "circulante", "outros_creditos"),
                ("ativo", "circulante", "cartao_corporativo"),
            ),
        )

    def nota_realizavel_lp(self) -> Nota | None:
        nota = self._nota_de_grupo(
            "realizavel_lp",
            "Realizável a Longo Prazo",
            ((("ativo", "nao_circulante", "realizavel_lp")),),
        )
        if nota is not None:
            return nota
        return self._nota_de_grupo(
            "realizavel_lp",
            "Realizável a Longo Prazo",
            ((("ativo", "nao_circulante", "outros_creditos")),),
        )

    def nota_imobilizado(self) -> Nota | None:
        """Tabela de movimentação, no formato do modelo de referência.

        O saldo anterior é derivado do balanço do exercício precedente quando
        ele foi enviado; aquisições, baixas e a depreciação do período não
        constam do balanço e ficam editáveis no passo de revisão.
        """
        imob = self._caminho(
            self._atual.balanco, "ativo", "nao_circulante", "imobilizado"
        )
        if not imob or not imob.get("grupos"):
            return None

        anterior = self._exercicios[1] if len(self._exercicios) > 1 else None
        imob_anterior = (
            self._caminho(anterior.balanco, "ativo", "nao_circulante", "imobilizado")
            if anterior
            else None
        )
        saldos_anteriores = {
            _normalizar(g["nome"]): g.get("custo", 0.0)
            for g in (imob_anterior or {}).get("grupos", [])
        }

        intangivel = self._caminho(
            self._atual.balanco, "ativo", "nao_circulante", "intangivel"
        )

        linhas: list[list[str]] = []
        for grupo in imob["grupos"]:
            chave = _normalizar(grupo["nome"])
            linhas.append(
                [
                    _titulo_legivel(grupo["nome"]),
                    formatar_brl(saldos_anteriores.get(chave, 0.0)),
                    formatar_brl(0.0),  # aquisições — editável
                    formatar_brl(0.0),  # baixas — editável
                    formatar_brl(0.0),  # depreciação do período — editável
                    formatar_brl(grupo.get("custo")),
                ]
            )

        intangivel_saldo_anterior = (
            (
                self._caminho(anterior.balanco, "ativo", "nao_circulante", "intangivel")
                or {}
            ).get("total")
            or 0.0
            if anterior
            else 0.0
        )
        if intangivel and intangivel.get("total"):
            linhas.append(
                [
                    "Intangível",
                    formatar_brl(intangivel_saldo_anterior),
                    formatar_brl(0.0),
                    formatar_brl(0.0),
                    formatar_brl(0.0),
                    formatar_brl(intangivel["total"]),
                ]
            )

        deprec_atual = imob.get("depreciacao_total") or 0.0
        deprec_anterior = (imob_anterior or {}).get("depreciacao_total") or 0.0
        linhas.append(
            [
                "(-) Depreciação Acumulada",
                formatar_brl(-deprec_anterior if deprec_anterior else 0.0),
                formatar_brl(0.0),
                formatar_brl(0.0),
                formatar_brl(-(deprec_atual - deprec_anterior))
                if deprec_anterior
                else formatar_brl(0.0),
                formatar_brl(-deprec_atual),
            ]
        )

        # Os dois totais somam as mesmas parcelas (bens + intangível − depreciação).
        total_anterior = (
            sum(saldos_anteriores.values())
            + intangivel_saldo_anterior
            - deprec_anterior
        )
        total_atual = (imob.get("total_liquido") or 0.0) + (
            (intangivel or {}).get("total") or 0.0
        )

        anterior_rotulo = (
            f"Saldo {anterior.ano}" if anterior else "Saldo anterior"
        )
        tabela = Tabela(
            titulo="a) Valor contábil",
            colunas=[
                "Imobilizado/Intangível",
                anterior_rotulo,
                "Aquisições",
                "Baixas",
                "Depreciação",
                f"Saldo {self._atual.ano}",
            ],
            linhas=linhas,
            total=[
                "Total Imobilizado",
                formatar_brl(total_anterior),
                formatar_brl(0.0),
                formatar_brl(0.0),
                formatar_brl(
                    -(deprec_atual - deprec_anterior) if deprec_anterior else 0.0
                ),
                formatar_brl(total_atual),
            ],
        )

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(
                "imobilizado",
                total=formatar_brl(total_atual),
                depreciacao=formatar_brl(deprec_atual),
            )
        )
        conteudo.insert(0, tabela)
        return Nota(numero=0, titulo="Imobilizado", tipo="misto", conteudo=conteudo)

    def nota_fornecedores(self) -> Nota | None:
        return self._nota_de_grupo(
            "fornecedores",
            "Fornecedores",
            ((("passivo", "circulante", "fornecedores")),),
        )

    def nota_emprestimos(self) -> Nota | None:
        return self._nota_de_grupo(
            "emprestimos",
            "Empréstimos e Financiamentos",
            ((("passivo", "circulante", "emprestimos")),),
        )

    def nota_obrigacoes_trabalhistas(self) -> Nota | None:
        return self._nota_de_grupo(
            "obrigacoes_trabalhistas",
            "Obrigações Trabalhistas",
            ((("passivo", "circulante", "obrigacoes_trabalhistas")),),
        )

    def nota_obrigacoes_fiscais(self) -> Nota | None:
        return self._nota_de_grupo(
            "obrigacoes_fiscais",
            "Obrigações Fiscais",
            (
                ("passivo", "circulante", "obrigacoes_fiscais"),
                ("passivo", "circulante", "parcelamentos"),
            ),
        )

    def nota_adiantamento_clientes(self) -> Nota | None:
        return self._nota_de_grupo(
            "adiantamento_clientes",
            "Adiantamento de Clientes",
            ((("passivo", "circulante", "adiantamento_clientes")),),
        )

    def nota_outras_obrigacoes(self) -> Nota | None:
        return self._nota_de_grupo(
            "outras_obrigacoes",
            "Outras Obrigações",
            ((("passivo", "circulante", "outras_obrigacoes")),),
        )

    def nota_provisoes(self) -> Nota | None:
        return self._nota_de_grupo(
            "provisoes", "Provisões", ((("passivo", "circulante", "provisoes")),)
        )

    def nota_capital_social(self, empresa: dict[str, Any]) -> Nota | None:
        capital = positivo(
            self._caminho(self._atual.balanco, "patrimonio_liquido", "capital_social")
        )
        if capital is None:
            return None

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos("capital_social", capital=formatar_brl(capital))
        )

        socios = empresa.get("socios") or []
        if socios:
            conteudo.append(
                Tabela(
                    titulo="Quadro societário",
                    colunas=["Sócio", "Participação"],
                    linhas=[
                        [socio.get("nome", ""), socio.get("participacao") or ""]
                        for socio in socios
                    ],
                    total=["Total", f"R$ {formatar_brl(capital)}"],
                )
            )

        return Nota(numero=0, titulo="Capital Social", tipo="misto", conteudo=conteudo)

    def nota_receita(self) -> Nota | None:
        if all(e.dre.get("receita_bruta") is None for e in self._exercicios):
            return None

        def linha(rotulo: str, chave: str) -> list[str]:
            return [rotulo] + [
                formatar_brl(positivo(e.dre.get(chave))) for e in self._exercicios
            ]

        tabela = Tabela(
            colunas=["Receita Operacional Bruta"] + self._anos,
            linhas=[
                linha("Receita Bruta", "receita_bruta"),
                linha("(-) Deduções da Receita Bruta", "deducoes"),
            ],
            total=["Receita Operacional Líquida"]
            + [
                formatar_brl(positivo(e.dre.get("receita_liquida")))
                for e in self._exercicios
            ],
        )

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(
                "receita",
                receita_bruta=formatar_brl(positivo(self._atual.dre.get("receita_bruta"))),
                receita_liquida=formatar_brl(
                    positivo(self._atual.dre.get("receita_liquida"))
                ),
            )
        )
        conteudo.append(tabela)
        return Nota(
            numero=0,
            titulo="Receita Operacional Líquida",
            tipo="misto",
            conteudo=conteudo,
        )

    def nota_natureza_despesas(self) -> Nota | None:
        """Matriz Custos x Despesas Gerais e Administrativas, uma tabela por exercício."""
        if all(not e.dre for e in self._exercicios):
            return None

        conteudo: list[Paragrafo | Tabela] = list(self._paragrafos("natureza_despesas"))
        gerou = False

        for exercicio in self._exercicios:
            dre = exercicio.dre
            if not dre:
                continue

            custos = dre.get("custos") or {}
            despesas = dre.get("despesas_operacionais") or {}

            custo_servico = abs(custos.get("custos_aplicados") or 0.0) + abs(
                custos.get("mao_obra_direta") or 0.0
            )
            servicos = abs(despesas.get("servicos_terceiros") or 0.0)
            depreciacoes = abs(despesas.get("depreciacoes") or 0.0)
            total_despesas = abs(despesas.get("total") or 0.0)
            outros = max(total_despesas - servicos - depreciacoes, 0.0)

            linhas = [
                ["Custo do Serviço Prestado", formatar_brl(custo_servico), formatar_brl(0.0), formatar_brl(custo_servico)],
                ["Serviços de Terceiros", formatar_brl(0.0), formatar_brl(servicos), formatar_brl(servicos)],
                ["Depreciações", formatar_brl(0.0), formatar_brl(depreciacoes), formatar_brl(depreciacoes)],
                ["Outros Custos e Despesas", formatar_brl(0.0), formatar_brl(outros), formatar_brl(outros)],
            ]

            conteudo.append(
                Tabela(
                    titulo=f"Exercício de {exercicio.ano}",
                    colunas=[
                        "Natureza dos Custos e Despesas",
                        "Custos",
                        "Despesas Gerais e Administrativas",
                        "Total",
                    ],
                    linhas=linhas,
                    total=[
                        "Total",
                        formatar_brl(custo_servico),
                        formatar_brl(servicos + depreciacoes + outros),
                        formatar_brl(custo_servico + servicos + depreciacoes + outros),
                    ],
                )
            )
            gerou = True

        if not gerou:
            return None

        return Nota(
            numero=0,
            titulo="Informações sobre a Natureza das Despesas e Custos",
            tipo="misto",
            conteudo=conteudo,
        )

    def nota_resultado_financeiro(self) -> Nota | None:
        rf_atual = self._atual.dre.get("resultado_financeiro") or {}
        if not rf_atual or all(v is None for v in rf_atual.values()):
            return None

        def linha(rotulo: str, chave: str, *, negativo: bool = False) -> list[str]:
            valores = []
            for e in self._exercicios:
                rf = e.dre.get("resultado_financeiro") or {}
                valor = positivo(rf.get(chave))
                if valor is not None and negativo:
                    valor = -valor
                valores.append(formatar_brl(valor))
            return [rotulo] + valores

        tabela = Tabela(
            colunas=["Descrição"] + self._anos,
            linhas=[
                linha("Receitas Financeiras", "receitas_financeiras"),
                linha("Outras Despesas Financeiras", "despesas_financeiras", negativo=True),
            ],
            total=["Resultado Financeiro"]
            + [
                formatar_brl((e.dre.get("resultado_financeiro") or {}).get("liquido"))
                for e in self._exercicios
            ],
        )

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos("resultado_financeiro")
        )
        conteudo.append(tabela)
        return Nota(
            numero=0, titulo="Resultado Financeiro", tipo="misto", conteudo=conteudo
        )

    def nota_aprovacao(
        self, empresa: dict[str, Any], config: dict[str, Any]
    ) -> Nota | None:
        return Nota(
            numero=0,
            titulo="Aprovação das Demonstrações Financeiras",
            tipo="texto",
            conteudo=list(self._paragrafos("aprovacao")),
        )
