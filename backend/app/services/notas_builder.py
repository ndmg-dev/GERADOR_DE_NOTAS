"""Montagem da estrutura das Notas Explicativas a partir dos dados extraídos.

Cada nota é um objeto :class:`Nota` contendo blocos ordenados de parágrafo e
tabela. Notas cujos grupos não existem no balanço (ex.: intangível zerado) são
automaticamente omitidas, e a numeração final é sequencial sobre as notas que
sobraram.

Os textos descritivos vêm de arquivos ``.txt`` em ``app/templates/notas/``,
permitindo que o time contábil os edite sem alterar código. Os parâmetros
dinâmicos usam a sintaxe ``{empresa.nome}``, ``{config.ano}`` etc.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "notas"

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][\w]*(?:\.[\w]+)*)\}")


def formatar_brl(valor: float | None, *, vazio: str = "-") -> str:
    """Formata 1566336.51 → '1.566.336,51'."""
    if valor is None:
        return vazio
    inteiro = f"{abs(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"-{inteiro}" if valor < 0 else inteiro


def positivo(valor: float | None) -> float | None:
    """Valores de passivo/PL vêm credores (negativos); as notas exibem o módulo."""
    return None if valor is None else abs(valor)


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
    tipo: Literal["tabela"] = "tabela"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
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


# --------------------------------------------------------------------------- #
# Serviço
# --------------------------------------------------------------------------- #


class NotasBuilderService:
    """Recebe os dicts do parser e monta a lista ordenada de notas."""

    TEMPLATES = {
        "contexto": "nota_01_contexto.txt",
        "apresentacao": "nota_02_apresentacao.txt",
        "praticas": "nota_03_praticas.txt",
        "caixa": "nota_04_caixa.txt",
        "clientes": "nota_05_clientes.txt",
        "outros_creditos": "nota_06_outros_creditos.txt",
        "realizavel_lp": "nota_07_realizavel_lp.txt",
        "imobilizado": "nota_08_imobilizado.txt",
        "intangivel": "nota_09_intangivel.txt",
        "fornecedores": "nota_10_fornecedores.txt",
        "obrigacoes_tributarias": "nota_11_obrigacoes_tributarias.txt",
        "obrigacoes_trabalhistas": "nota_12_obrigacoes_trabalhistas.txt",
        "outras_obrigacoes": "nota_13_outras_obrigacoes.txt",
        "capital_social": "nota_14_capital_social.txt",
        "patrimonio_liquido": "nota_15_patrimonio_liquido.txt",
        "receita": "nota_16_receita.txt",
        "custos_despesas": "nota_17_custos_despesas.txt",
        "resultado_financeiro": "nota_18_resultado_financeiro.txt",
        "resultado_exercicio": "nota_19_resultado_exercicio.txt",
        "aprovacao": "nota_20_aprovacao.txt",
    }

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._contexto: dict[str, Any] = {}

    # ------------------------------------------------------------ Templates

    def _render(self, chave: str, **extra: Any) -> list[str]:
        """Lê o template e devolve seus parágrafos com os placeholders resolvidos."""
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
        balanco: dict[str, Any],
        dre: dict[str, Any],
        empresa: dict[str, Any],
        config: dict[str, Any],
    ) -> list[Nota]:
        self._contexto = {
            "empresa": empresa,
            "config": config,
            "ano": config.get("ano"),
            "ano_anterior": (config.get("ano") or 0) - 1,
        }

        candidatas = [
            self.nota_contexto_operacional(empresa),
            self.nota_apresentacao(config),
            self.nota_praticas_contabeis(balanco),
            self.nota_caixa(balanco),
            self.nota_clientes(balanco),
            self.nota_outros_creditos(balanco),
            self.nota_realizavel_lp(balanco),
            self.nota_imobilizado(balanco),
            self.nota_intangivel(balanco),
            self.nota_fornecedores(balanco),
            self.nota_obrigacoes_tributarias(balanco),
            self.nota_obrigacoes_trabalhistas(balanco),
            self.nota_outras_obrigacoes(balanco),
            self.nota_capital_social(balanco, empresa),
            self.nota_patrimonio_liquido(balanco),
            self.nota_receita(dre),
            self.nota_custos_despesas(dre),
            self.nota_resultado_financeiro(dre),
            self.nota_resultado_exercicio(dre),
            self.nota_aprovacao(empresa, config),
        ]

        notas = [n for n in candidatas if n is not None]
        for numero, nota in enumerate(notas, start=1):
            nota.numero = numero

        logger.info("Notas montadas: %d de %d possíveis", len(notas), len(candidatas))
        return notas

    # ------------------------------------------------------------ Auxiliares

    @property
    def _ano(self) -> str:
        return str(self._contexto.get("ano") or "")

    def _tabela_de_grupo(
        self,
        grupo: dict[str, Any] | None,
        *,
        rotulo_total: str = "Total",
        usar_modulo: bool = False,
    ) -> Tabela | None:
        """Converte ``{"total":..., "itens":[...]}`` em uma tabela de duas colunas."""
        if not grupo:
            return None

        def preparar(valor: float | None) -> float | None:
            return positivo(valor) if usar_modulo else valor

        linhas = [
            [item["descricao"], formatar_brl(preparar(item["valor"]))]
            for item in grupo.get("itens", [])
        ]
        total = preparar(grupo.get("total"))

        if not linhas and total is None:
            return None
        if not linhas:
            linhas = [[grupo.get("descricao", rotulo_total), formatar_brl(total)]]

        return Tabela(
            colunas=["Descrição", self._ano],
            linhas=linhas,
            total=[rotulo_total, formatar_brl(total)],
        )

    def _nota_de_grupo(
        self,
        chave_template: str,
        titulo: str,
        grupo: dict[str, Any] | None,
        *,
        usar_modulo: bool = False,
    ) -> Nota | None:
        tabela = self._tabela_de_grupo(grupo, usar_modulo=usar_modulo)
        if tabela is None:
            return None

        total = positivo(grupo.get("total")) if usar_modulo else grupo.get("total")
        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(chave_template, total=formatar_brl(total))
        )
        conteudo.append(tabela)
        return Nota(numero=0, titulo=titulo, tipo="misto", conteudo=conteudo)

    # ---------------------------------------------------------------- Notas

    def nota_contexto_operacional(self, empresa: dict[str, Any]) -> Nota | None:
        return Nota(
            numero=0,
            titulo="Contexto Operacional",
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

    def nota_praticas_contabeis(self, balanco: dict[str, Any]) -> Nota | None:
        return Nota(
            numero=0,
            titulo="Principais Práticas Contábeis Adotadas",
            tipo="texto",
            conteudo=list(self._paragrafos("praticas")),
        )

    def nota_caixa(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(balanco, "ativo", "circulante", "caixa_equivalentes")
        return self._nota_de_grupo("caixa", "Caixa e Equivalentes de Caixa", grupo)

    def nota_clientes(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(balanco, "ativo", "circulante", "clientes")
        return self._nota_de_grupo("clientes", "Clientes", grupo)

    def nota_outros_creditos(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(balanco, "ativo", "circulante", "outros_creditos")
        return self._nota_de_grupo("outros_creditos", "Outros Créditos", grupo)

    def nota_realizavel_lp(self, balanco: dict[str, Any]) -> Nota | None:
        nao_circulante = self._caminho(balanco, "ativo", "nao_circulante") or {}
        grupo = nao_circulante.get("realizavel_lp") or nao_circulante.get(
            "outros_creditos"
        )
        return self._nota_de_grupo(
            "realizavel_lp", "Ativo Realizável a Longo Prazo", grupo
        )

    def nota_imobilizado(self, balanco: dict[str, Any]) -> Nota | None:
        imob = self._caminho(balanco, "ativo", "nao_circulante", "imobilizado")
        if not imob or not imob.get("grupos"):
            return None

        linhas = [
            [
                grupo["nome"],
                formatar_brl(grupo.get("custo")),
                formatar_brl(-abs(grupo["depreciacao"])) if grupo.get("depreciacao") else "-",
                formatar_brl(grupo.get("liquido")),
            ]
            for grupo in imob["grupos"]
        ]

        tabela = Tabela(
            colunas=["Descrição", "Custo", "Depreciação Acumulada", "Valor Líquido"],
            linhas=linhas,
            total=[
                "Total",
                formatar_brl(imob.get("total_custo")),
                formatar_brl(
                    -abs(imob["depreciacao_total"])
                    if imob.get("depreciacao_total")
                    else None
                ),
                formatar_brl(imob.get("total_liquido")),
            ],
        )

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(
                "imobilizado",
                total=formatar_brl(imob.get("total_liquido")),
                depreciacao=formatar_brl(imob.get("depreciacao_total")),
            )
        )
        conteudo.append(tabela)
        return Nota(numero=0, titulo="Imobilizado", tipo="misto", conteudo=conteudo)

    def nota_intangivel(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(balanco, "ativo", "nao_circulante", "intangivel")
        if not grupo or not grupo.get("total"):
            return None
        return self._nota_de_grupo("intangivel", "Intangível", grupo)

    def nota_fornecedores(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(balanco, "passivo", "circulante", "fornecedores")
        return self._nota_de_grupo(
            "fornecedores", "Fornecedores", grupo, usar_modulo=True
        )

    def nota_obrigacoes_tributarias(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(balanco, "passivo", "circulante", "obrigacoes_tributarias")
        return self._nota_de_grupo(
            "obrigacoes_tributarias", "Obrigações Tributárias", grupo, usar_modulo=True
        )

    def nota_obrigacoes_trabalhistas(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(
            balanco, "passivo", "circulante", "obrigacoes_trabalhistas"
        )
        return self._nota_de_grupo(
            "obrigacoes_trabalhistas",
            "Obrigações Trabalhistas e Previdenciárias",
            grupo,
            usar_modulo=True,
        )

    def nota_outras_obrigacoes(self, balanco: dict[str, Any]) -> Nota | None:
        grupo = self._caminho(balanco, "passivo", "circulante", "outras_obrigacoes")
        return self._nota_de_grupo(
            "outras_obrigacoes", "Outras Obrigações", grupo, usar_modulo=True
        )

    def nota_capital_social(
        self, balanco: dict[str, Any], empresa: dict[str, Any]
    ) -> Nota | None:
        capital = positivo(self._caminho(balanco, "patrimonio_liquido", "capital_social"))
        if capital is None:
            return None

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos("capital_social", capital=formatar_brl(capital))
        )

        socios = empresa.get("socios") or []
        if socios:
            conteudo.append(
                Tabela(
                    colunas=["Sócio", "CPF", "Participação"],
                    linhas=[
                        [
                            socio.get("nome", ""),
                            socio.get("cpf", "") or "",
                            socio.get("participacao", "") or "",
                        ]
                        for socio in socios
                    ],
                    total=["Total", "", formatar_brl(capital)],
                )
            )

        return Nota(numero=0, titulo="Capital Social", tipo="misto", conteudo=conteudo)

    def nota_patrimonio_liquido(self, balanco: dict[str, Any]) -> Nota | None:
        pl = balanco.get("patrimonio_liquido") or {}
        campos = [
            ("Capital Social", pl.get("capital_social")),
            ("Reservas de Lucros", pl.get("reservas")),
            ("Ajustes de Avaliação Patrimonial", pl.get("ajustes")),
        ]
        linhas = [
            [rotulo, formatar_brl(positivo(valor))]
            for rotulo, valor in campos
            if valor is not None
        ]
        if not linhas:
            return None

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(
                "patrimonio_liquido", total=formatar_brl(positivo(pl.get("total")))
            )
        )
        conteudo.append(
            Tabela(
                colunas=["Descrição", self._ano],
                linhas=linhas,
                total=["Total", formatar_brl(positivo(pl.get("total")))],
            )
        )
        return Nota(
            numero=0, titulo="Patrimônio Líquido", tipo="misto", conteudo=conteudo
        )

    def nota_receita(self, dre: dict[str, Any]) -> Nota | None:
        campos = [
            ("Receita Operacional Bruta", dre.get("receita_bruta")),
            ("(-) Deduções da Receita Bruta", dre.get("deducoes")),
        ]
        linhas = [
            [rotulo, formatar_brl(positivo(valor))]
            for rotulo, valor in campos
            if valor is not None
        ]
        if not linhas:
            return None

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(
                "receita",
                receita_bruta=formatar_brl(positivo(dre.get("receita_bruta"))),
                receita_liquida=formatar_brl(positivo(dre.get("receita_liquida"))),
            )
        )
        conteudo.append(
            Tabela(
                colunas=["Descrição", self._ano],
                linhas=linhas,
                total=[
                    "Receita Operacional Líquida",
                    formatar_brl(positivo(dre.get("receita_liquida"))),
                ],
            )
        )
        return Nota(
            numero=0, titulo="Receita Operacional Líquida", tipo="misto",
            conteudo=conteudo,
        )

    def nota_custos_despesas(self, dre: dict[str, Any]) -> Nota | None:
        custos = dre.get("custos") or {}
        despesas = dre.get("despesas_operacionais") or {}

        campos = [
            ("Custos Aplicados", custos.get("custos_aplicados")),
            ("Mão de Obra Direta", custos.get("mao_obra_direta")),
            ("Despesas com Pessoal", despesas.get("despesas_pessoal")),
            ("Impostos, Taxas e Contribuições", despesas.get("impostos_taxas")),
            ("Despesas Gerais", despesas.get("despesas_gerais")),
        ]
        linhas = [
            [rotulo, formatar_brl(positivo(valor))]
            for rotulo, valor in campos
            if valor is not None
        ]
        if not linhas:
            return None

        total = None
        if custos.get("custos_aplicados") is not None or despesas.get("total") is not None:
            total = abs(custos.get("custos_aplicados") or 0.0) + abs(
                despesas.get("total") or 0.0
            )

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos(
                "custos_despesas",
                despesas_total=formatar_brl(positivo(despesas.get("total"))),
            )
        )
        conteudo.append(
            Tabela(
                colunas=["Descrição", self._ano],
                linhas=linhas,
                total=["Total", formatar_brl(total)],
            )
        )
        return Nota(
            numero=0, titulo="Custos e Despesas Operacionais", tipo="misto",
            conteudo=conteudo,
        )

    def nota_resultado_financeiro(self, dre: dict[str, Any]) -> Nota | None:
        rf = dre.get("resultado_financeiro") or {}
        campos = [
            ("Receitas Financeiras", rf.get("receitas_financeiras")),
            ("(-) Despesas Financeiras", rf.get("despesas_financeiras")),
        ]
        linhas = [
            [rotulo, formatar_brl(positivo(valor))]
            for rotulo, valor in campos
            if valor is not None
        ]
        if not linhas:
            return None

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos("resultado_financeiro")
        )
        conteudo.append(
            Tabela(
                colunas=["Descrição", self._ano],
                linhas=linhas,
                total=[
                    "Resultado Financeiro Líquido",
                    formatar_brl(positivo(rf.get("liquido"))),
                ],
            )
        )
        return Nota(
            numero=0, titulo="Resultado Financeiro", tipo="misto", conteudo=conteudo
        )

    def nota_resultado_exercicio(self, dre: dict[str, Any]) -> Nota | None:
        lucro = dre.get("lucro_liquido")
        if lucro is None:
            return None

        campos = [
            ("Resultado Operacional", dre.get("resultado_operacional")),
            ("Outras Receitas", dre.get("outras_receitas")),
        ]
        linhas = [
            [rotulo, formatar_brl(positivo(valor))]
            for rotulo, valor in campos
            if valor is not None
        ]

        conteudo: list[Paragrafo | Tabela] = list(
            self._paragrafos("resultado_exercicio", lucro=formatar_brl(positivo(lucro)))
        )
        if linhas:
            conteudo.append(
                Tabela(
                    colunas=["Descrição", self._ano],
                    linhas=linhas,
                    total=["Resultado Líquido do Exercício", formatar_brl(positivo(lucro))],
                )
            )
        return Nota(
            numero=0, titulo="Resultado do Exercício", tipo="misto", conteudo=conteudo
        )

    def nota_aprovacao(
        self, empresa: dict[str, Any], config: dict[str, Any]
    ) -> Nota | None:
        return Nota(
            numero=0,
            titulo="Aprovação das Demonstrações Contábeis",
            tipo="texto",
            conteudo=list(self._paragrafos("aprovacao")),
        )

    # ------------------------------------------------------------ Utilitário

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
