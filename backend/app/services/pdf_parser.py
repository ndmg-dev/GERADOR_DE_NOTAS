"""Extração e estruturação dos dados dos PDFs do sistema contábil Domínio.

Os relatórios do Domínio têm camada de texto nativa e seguem o padrão:

    Descrição              Saldo Atual
    CONTA PRINCIPAL        9.999.999,99D
      subconta nivel 1     1.111,11D
        subconta nivel 2   222,22C

Onde ``D`` = débito (natureza devedora) e ``C`` = crédito (natureza credora,
representada com sinal negativo).

O parser é tolerante: qualquer conta ausente no PDF resulta em ``None`` para o
campo correspondente, nunca em exceção.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Marcadores e padrões (spec seção 9.1)
# --------------------------------------------------------------------------- #

SECTION_MARKERS = {
    "ativo_circulante": "ATIVO CIRCULANTE",
    "ativo_nao_circulante": "ATIVO NÃO-CIRCULANTE",
    "passivo_circulante": "PASSIVO CIRCULANTE",
    "patrimonio_liquido": "PATRIMÔNIO LÍQUIDO",
}

ACCOUNT_PATTERNS = {
    "caixa_total": r"CAIXA E EQUIVALENTE DE CAIXA\s+([\d.,]+)[DC]",
    "clientes_total": r"CLIENTES\s+([\d.,]+)[DC]",
    "imobilizado_total": r"IMOBILIZADO\s+([\d.,]+)[DC]",
    "depreciacao_acumulada": r"\(-\) DEPRECIA[ÇC][ÕO]ES.*?\s+([\d.,]+)[DC]",
    "fornecedores": r"FORNECEDORES\s+([\d.,]+)[DC]",
    "patrimonio_liquido": r"PATRIMÔNIO LÍQUIDO\s+([\d.,]+)[DC]",
}

# Linha de conta: descrição + valor com natureza D/C opcional.
# O separador é \s+ (e não \s{2,}) porque descrições longas colapsam o
# espaçamento para um único espaço na extração do PDF.
_LINE_RE = re.compile(
    r"^(?P<descricao>.+?)\s+(?P<valor>\(?-?[\d.]+,\d{2}\)?)\s*(?P<natureza>[DC])?\s*$"
)
_VALUE_RE = re.compile(r"^\(?\s*(?P<sinal>-)?\s*(?P<numero>[\d.]*\d(?:,\d{1,2})?)\s*\)?\s*(?P<natureza>[DC])?$")

# Linhas de cabeçalho/rodapé do relatório que devem ser ignoradas.
_NOISE_PATTERNS = (
    r"^\s*P[áa]gina\s+\d+",
    r"^\s*Descri[çc][ãa]o\s+Saldo",
    r"^\s*Folha\s+\d+",
    r"^\s*Emitido\s+em",
    r"^\s*CNPJ",
    r"^\s*Per[íi]odo",
    r"^-{3,}$",
)
_NOISE_RE = re.compile("|".join(_NOISE_PATTERNS), re.IGNORECASE)


def _normalizar(texto: str) -> str:
    """Maiúsculas, sem acentos, sem pontuação de apoio e espaços colapsados."""
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    sem_acento = sem_acento.upper()
    sem_acento = sem_acento.replace("(-)", " ").replace("(+)", " ")
    sem_acento = re.sub(r"[^A-Z0-9 ]+", " ", sem_acento)
    return re.sub(r"\s+", " ", sem_acento).strip()


TOLERANCIA = 0.005  # diferença aceitável ao comparar somas de centavos


@dataclass
class ContaLinha:
    """Uma linha de conta extraída do relatório."""

    descricao: str
    valor: float
    indent: int
    ordem: int
    normalizada: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.normalizada:
            self.normalizada = _normalizar(self.descricao)

    def to_item(self) -> dict[str, Any]:
        return {"descricao": self.descricao.strip(), "valor": self.valor}


# --------------------------------------------------------------------------- #
# Rótulos de cada grupo de contas
# --------------------------------------------------------------------------- #

LABELS_BALANCO: dict[str, tuple[str, ...]] = {
    "caixa_equivalentes": (
        "CAIXA E EQUIVALENTE DE CAIXA",
        "CAIXA E EQUIVALENTES DE CAIXA",
        "DISPONIVEL",
        "DISPONIBILIDADES",
    ),
    "clientes": ("CLIENTES", "CONTAS A RECEBER", "DUPLICATAS A RECEBER"),
    "outros_creditos": ("OUTROS CREDITOS", "OUTROS CREDITOS A RECEBER"),
    "cartao_corporativo": (
        "CARTAO CORPORATIVO DE COLABORADORES",
        "CARTAO CORPORATIVO",
    ),
    "estoques": ("ESTOQUES",),
    "realizavel_lp": ("REALIZAVEL A LONGO PRAZO", "ATIVO REALIZAVEL A LONGO PRAZO"),
    "imobilizado": ("IMOBILIZADO", "ATIVO IMOBILIZADO"),
    "intangivel": ("INTANGIVEL", "ATIVO INTANGIVEL"),
    "fornecedores": ("FORNECEDORES", "FORNECEDORES NACIONAIS"),
    "obrigacoes_fiscais": (
        "OBRIGACOES TRIBUTARIAS",
        "OBRIGACOES FISCAIS",
        "IMPOSTOS E CONTRIBUICOES A RECOLHER",
    ),
    "parcelamentos": ("PARCELAMENTOS", "PARCELAMENTO"),
    # O relatório do Domínio usa o singular "TRABALHISTA E PREVIDENCIARIA".
    "obrigacoes_trabalhistas": (
        "OBRIGACOES TRABALHISTA E PREVIDENCIARIA",
        "OBRIGACOES TRABALHISTAS E PREVIDENCIARIAS",
        "OBRIGACOES TRABALHISTAS",
        "OBRIGACOES SOCIAIS E TRABALHISTAS",
        "OBRIGACOES COM PESSOAL",
    ),
    "adiantamento_clientes": (
        "ADIANTAMENTO DE CLIENTES",
        "ADIANTAMENTOS DE CLIENTES",
        "ADIANTAMENTO DE CLIENTE",
    ),
    "provisoes": ("PROVISOES", "PROVISAO"),
    "outras_obrigacoes": ("OUTRAS OBRIGACOES", "OUTRAS CONTAS A PAGAR"),
    "emprestimos": (
        "EMPRESTIMOS E FINANCIAMENTOS",
        "EMPRESTIMOS DIVERSOS",
        "FINANCIAMENTOS",
    ),
    "capital_social": ("CAPITAL SOCIAL", "CAPITAL SOCIAL REALIZADO"),
    "reservas": ("RESERVAS DE LUCROS", "RESERVAS", "LUCROS OU PREJUIZOS ACUMULADOS"),
    "ajustes": ("AJUSTES DE AVALIACAO PATRIMONIAL", "AJUSTES DE EXERCICIOS ANTERIORES"),
    "total_ativo": ("TOTAL DO ATIVO", "TOTAL GERAL DO ATIVO", "ATIVO"),
    "total_passivo_pl": (
        "TOTAL DO PASSIVO E PATRIMONIO LIQUIDO",
        "TOTAL DO PASSIVO",
        "TOTAL GERAL DO PASSIVO",
        "PASSIVO",
    ),
}

LABELS_DRE: dict[str, tuple[str, ...]] = {
    "receita_bruta": (
        "RECEITA BRUTA",
        "RECEITA OPERACIONAL BRUTA",
        "RECEITA BRUTA DE VENDAS",
        "RECEITAS OPERACIONAIS",
    ),
    "deducoes": (
        "DEDUCOES DA RECEITA BRUTA",
        "DEDUCOES DA RECEITA",
        "DEDUCOES",
        "IMPOSTOS INCIDENTES SOBRE VENDAS",
    ),
    "receita_liquida": ("RECEITA LIQUIDA", "RECEITA OPERACIONAL LIQUIDA"),
    "custos_aplicados": (
        "CUSTOS APLICADOS",
        "CUSTO DOS SERVICOS PRESTADOS",
        "CUSTO DAS MERCADORIAS VENDIDAS",
        "CUSTOS OPERACIONAIS",
        "CUSTOS",
    ),
    "mao_obra_direta": ("MAO DE OBRA DIRETA", "MAO DE OBRA"),
    "lucro_bruto": ("LUCRO BRUTO", "RESULTADO BRUTO"),
    "despesas_operacionais": (
        "DESPESAS OPERACIONAIS",
        "DESPESAS OPERACIONAIS ADMINISTRATIVAS",
    ),
    "despesas_administrativas": (
        "DESPESAS ADMINISTRATIVAS OP",
        "DESPESAS ADMINISTRATIVAS",
    ),
    "despesas_pessoal": ("DESPESAS COM PESSOAL", "DESPESAS DE PESSOAL"),
    "impostos_taxas": (
        "IMPOSTOS TAXAS E CONTRIBUICOES",
        "IMPOSTOS E TAXAS",
        "DESPESAS TRIBUTARIAS",
    ),
    "despesas_gerais": ("DESPESAS GERAIS", "DESPESAS GERAIS E ADMINISTRATIVAS"),
    "depreciacoes": ("DEPRECIACOES", "DEPRECIACAO E AMORTIZACAO"),
    "servicos_terceiros": ("SERVICOS DE TERCEIROS", "SERVICOS PRESTADOS POR TERCEIROS"),
    "receitas_financeiras": ("RECEITAS FINANCEIRAS",),
    "despesas_financeiras": ("DESPESAS FINANCEIRAS", "OUTRAS DESPESAS FINANCEIRAS"),
    "resultado_financeiro": ("RESULTADO FINANCEIRO OP", "RESULTADO FINANCEIRO"),
    "outras_receitas": (
        "OUTRAS RECEITAS OPERACIONAIS",
        "OUTRAS RECEITAS",
        "OUTRAS RECEITAS E DESPESAS",
    ),
    "resultado_outras": (
        "RESULTADO OUTRAS DESPESAS RECEITAS OP",
        "RESULTADO OUTRAS DESPESAS/RECEITAS OP",
    ),
    "resultado_operacional": ("RESULTADO OPERACIONAL", "LUCRO OPERACIONAL"),
    "lucro_liquido": (
        "LUCRO LIQUIDO DO EXERCICIO",
        "RESULTADO LIQUIDO DO EXERCICIO",
        "LUCRO LIQUIDO",
        "RESULTADO DO EXERCICIO",
    ),
}


class PdfParserService:
    """Extrai os dados estruturados do Balanço Patrimonial e da DRE."""

    MIN_CHARS_NATIVO = 100

    def __init__(self, ocr_service: Any | None = None) -> None:
        self._ocr_service = ocr_service

    # ------------------------------------------------------------- Extração

    def detect_extraction_method(self, pdf_path: str) -> str:
        """Retorna 'native' se há camada de texto suficiente, senão 'ocr'."""
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    return "ocr"
                texto = pdf.pages[0].extract_text() or ""
                return "native" if len(texto.strip()) > self.MIN_CHARS_NATIVO else "ocr"
        except Exception:
            logger.warning(
                "Falha ao inspecionar %s com pdfplumber; usando OCR", pdf_path,
                exc_info=True,
            )
            return "ocr"

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extração nativa — PDFs do Domínio têm camada de texto."""
        import pdfplumber

        partes: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for pagina in pdf.pages:
                partes.append(pagina.extract_text(layout=True) or "")
        return "\n".join(partes)

    def _extract_with_ocr(self, pdf_path: str) -> str:
        """Fallback: rasteriza com pdf2image e aplica tesseract pt+eng."""
        from app.services.ocr_service import OcrService

        servico = self._ocr_service or OcrService()
        return servico.extract_text(pdf_path)

    def extract_text(self, pdf_path: str) -> str:
        metodo = self.detect_extraction_method(pdf_path)
        logger.info("Extraindo %s via método '%s'", pdf_path, metodo)
        if metodo == "native":
            texto = self._extract_with_pdfplumber(pdf_path)
            if len(texto.strip()) > self.MIN_CHARS_NATIVO:
                return texto
            logger.info("Texto nativo insuficiente; caindo para OCR")
        return self._extract_with_ocr(pdf_path)

    # ------------------------------------------------------------- Valores

    def _parse_value(self, text: str) -> float | None:
        """Converte '1.566.336,51D' → 1566336.51 e '800.967,11C' → -800967.11."""
        if text is None:
            return None

        bruto = str(text).strip()
        if not bruto:
            return None

        negativo_parenteses = bruto.startswith("(") and bruto.endswith(")")
        bruto = bruto.strip("()").strip()
        bruto = bruto.replace(" ", "").replace("R$", "")

        match = _VALUE_RE.match(bruto)
        if not match:
            return None

        numero = match.group("numero").replace(".", "").replace(",", ".")
        try:
            valor = float(numero)
        except ValueError:
            return None

        if match.group("sinal") or negativo_parenteses:
            valor = -valor
        if match.group("natureza") == "C":
            valor = -abs(valor)

        return valor

    # --------------------------------------------------------- Tokenização

    def _parse_lines(self, texto: str) -> list[ContaLinha]:
        """Converte o texto bruto em linhas de conta com indentação preservada."""
        linhas: list[ContaLinha] = []
        ordem = 0

        for linha_bruta in texto.splitlines():
            if not linha_bruta.strip() or _NOISE_RE.search(linha_bruta):
                continue

            match = _LINE_RE.match(linha_bruta.rstrip())
            if not match:
                continue

            descricao = match.group("descricao").strip()
            if not descricao:
                continue

            valor_texto = match.group("valor") + (match.group("natureza") or "")
            valor = self._parse_value(valor_texto)
            if valor is None:
                continue

            indent = len(linha_bruta) - len(linha_bruta.lstrip())
            linhas.append(
                ContaLinha(descricao=descricao, valor=valor, indent=indent, ordem=ordem)
            )
            ordem += 1

        return linhas

    # ------------------------------------------------------------- Buscas

    def _encontrar(
        self,
        linhas: list[ContaLinha],
        rotulos: tuple[str, ...],
        *,
        inicio: int = 0,
        fim: int | None = None,
    ) -> ContaLinha | None:
        """Primeira linha cuja descrição casa com um dos rótulos (exato > prefixo)."""
        janela = linhas[inicio : fim if fim is not None else len(linhas)]
        rotulos_norm = [_normalizar(r) for r in rotulos]

        for rotulo in rotulos_norm:
            for linha in janela:
                if linha.normalizada == rotulo:
                    return linha
        for rotulo in rotulos_norm:
            for linha in janela:
                if linha.normalizada.startswith(rotulo):
                    return linha
        return None

    def _descendentes(
        self, linhas: list[ContaLinha], pai: ContaLinha
    ) -> list[ContaLinha]:
        """Todas as linhas subordinadas ao pai, em qualquer profundidade."""
        descendentes: list[ContaLinha] = []
        for linha in linhas:
            if linha.ordem <= pai.ordem:
                continue
            if linha.indent <= pai.indent:
                break
            descendentes.append(linha)
        return descendentes

    def _filhos(self, linhas: list[ContaLinha], pai: ContaLinha) -> list[ContaLinha]:
        """Apenas os filhos diretos do pai.

        Nos relatórios do Domínio a extração do PDF nem sempre preserva a
        indentação dos níveis mais profundos: contas sintéticas e analíticas
        saem na mesma coluna. Quando isso acontece, a hierarquia é
        reconstruída pela aritmética — uma conta sintética é igual à soma das
        analíticas que a seguem.
        """
        descendentes = self._descendentes(linhas, pai)

        # Subgrupo cujas analíticas saíram no mesmo recuo que ele: procura,
        # entre as linhas seguintes de mesmo nível, as que somam o seu valor.
        if not descendentes:
            return self._analiticas_no_mesmo_nivel(linhas, pai)

        menor_indent = min(linha.indent for linha in descendentes)
        candidatos = [l for l in descendentes if l.indent == menor_indent]

        # A indentação ainda separa os níveis: os candidatos já são os filhos.
        if len(candidatos) < len(descendentes):
            return candidatos

        return self._agrupar_por_soma(candidatos)

    def _analiticas_no_mesmo_nivel(
        self, linhas: list[ContaLinha], pai: ContaLinha
    ) -> list[ContaLinha]:
        """Linhas seguintes, de mesmo recuo, que somam exatamente o valor do pai."""
        seguintes = [
            l for l in linhas if l.ordem > pai.ordem and l.indent == pai.indent
        ]
        if not seguintes:
            return []

        soma = 0.0
        candidatas: list[ContaLinha] = []
        for linha in seguintes:
            soma += linha.valor
            candidatas.append(linha)
            if abs(soma - pai.valor) <= TOLERANCIA:
                return self._agrupar_por_soma(candidatas)
            if abs(soma) > abs(pai.valor) + TOLERANCIA:
                break
        return []

    @staticmethod
    def _agrupar_por_soma(linhas: list[ContaLinha]) -> list[ContaLinha]:
        """Filtra, de uma lista achatada, as contas de primeiro nível.

        Percorre as linhas em ordem: se as linhas seguintes somam exatamente o
        valor da linha atual, elas são suas analíticas e são descartadas deste
        nível.
        """
        filhos: list[ContaLinha] = []
        indice = 0

        while indice < len(linhas):
            atual = linhas[indice]
            filhos.append(atual)

            soma = 0.0
            consumidos = 0
            seguinte = indice + 1

            while seguinte < len(linhas):
                soma += linhas[seguinte].valor
                consumidos += 1
                seguinte += 1
                if abs(soma - atual.valor) <= TOLERANCIA:
                    break
                # A soma ultrapassou o pai (em módulo): não são suas analíticas.
                if abs(soma) > abs(atual.valor) + TOLERANCIA:
                    consumidos = 0
                    break

            if consumidos and abs(soma - atual.valor) <= TOLERANCIA:
                indice += 1 + consumidos
            else:
                indice += 1

        return filhos

    def _grupo(
        self,
        linhas: list[ContaLinha],
        rotulos: tuple[str, ...],
        *,
        inicio: int = 0,
        fim: int | None = None,
    ) -> dict[str, Any] | None:
        """Monta ``{"total": float, "itens": [...]}`` ou ``None`` se ausente."""
        linha = self._encontrar(linhas, rotulos, inicio=inicio, fim=fim)
        if linha is None:
            return None

        filhos = self._filhos(linhas, linha)
        return {
            "descricao": linha.descricao,
            "total": linha.valor,
            "itens": [f.to_item() for f in filhos],
        }

    def _valor(
        self,
        linhas: list[ContaLinha],
        rotulos: tuple[str, ...],
        *,
        inicio: int = 0,
        fim: int | None = None,
    ) -> float | None:
        linha = self._encontrar(linhas, rotulos, inicio=inicio, fim=fim)
        return linha.valor if linha else None

    def _indice_secao(self, linhas: list[ContaLinha], marcador: str) -> int | None:
        alvo = _normalizar(marcador)
        for linha in linhas:
            if linha.normalizada.startswith(alvo):
                return linha.ordem
        return None

    # ------------------------------------------------------------- Balanço

    def parse_balanco(self, pdf_path: str) -> dict[str, Any]:
        texto = self.extract_text(pdf_path)
        return self.parse_balanco_text(texto)

    def parse_balanco_text(self, texto: str) -> dict[str, Any]:
        """Versão testável: recebe o texto já extraído do PDF."""
        linhas = self._parse_lines(texto)

        i_ac = self._indice_secao(linhas, SECTION_MARKERS["ativo_circulante"])
        i_anc = self._indice_secao(linhas, SECTION_MARKERS["ativo_nao_circulante"])
        i_pc = self._indice_secao(linhas, SECTION_MARKERS["passivo_circulante"])
        i_pl = self._indice_secao(linhas, SECTION_MARKERS["patrimonio_liquido"])

        fim_ac = i_anc if i_anc is not None else i_pc
        fim_anc = i_pc if i_pc is not None else i_pl
        fim_pc = i_pl

        circulante = {
            "caixa_equivalentes": self._grupo(
                linhas, LABELS_BALANCO["caixa_equivalentes"],
                inicio=i_ac or 0, fim=fim_ac,
            ),
            "clientes": self._grupo(
                linhas, LABELS_BALANCO["clientes"], inicio=i_ac or 0, fim=fim_ac
            ),
            "estoques": self._grupo(
                linhas, LABELS_BALANCO["estoques"], inicio=i_ac or 0, fim=fim_ac
            ),
            "outros_creditos": self._grupo(
                linhas, LABELS_BALANCO["outros_creditos"], inicio=i_ac or 0, fim=fim_ac
            ),
            "cartao_corporativo": self._grupo(
                linhas,
                LABELS_BALANCO["cartao_corporativo"],
                inicio=i_ac or 0,
                fim=fim_ac,
            ),
            "total": self._valor(
                linhas, (SECTION_MARKERS["ativo_circulante"],), inicio=i_ac or 0
            ),
        }

        nao_circulante = {
            "realizavel_lp": self._grupo(
                linhas, LABELS_BALANCO["realizavel_lp"],
                inicio=i_anc or 0, fim=fim_anc,
            ),
            "outros_creditos": self._grupo(
                linhas, LABELS_BALANCO["outros_creditos"],
                inicio=i_anc or 0, fim=fim_anc,
            ),
            "imobilizado": self._parse_imobilizado(
                linhas, inicio=i_anc or 0, fim=fim_anc
            ),
            "intangivel": self._parse_intangivel(
                linhas, inicio=i_anc or 0, fim=fim_anc
            ),
            "total": self._valor(
                linhas, (SECTION_MARKERS["ativo_nao_circulante"],), inicio=i_anc or 0
            ),
        }

        passivo_circulante = {
            "fornecedores": self._grupo(
                linhas, LABELS_BALANCO["fornecedores"], inicio=i_pc or 0, fim=fim_pc
            ),
            "obrigacoes_fiscais": self._grupo(
                linhas, LABELS_BALANCO["obrigacoes_fiscais"],
                inicio=i_pc or 0, fim=fim_pc,
            ),
            "parcelamentos": self._grupo(
                linhas, LABELS_BALANCO["parcelamentos"], inicio=i_pc or 0, fim=fim_pc
            ),
            "obrigacoes_trabalhistas": self._grupo(
                linhas, LABELS_BALANCO["obrigacoes_trabalhistas"],
                inicio=i_pc or 0, fim=fim_pc,
            ),
            "adiantamento_clientes": self._grupo(
                linhas, LABELS_BALANCO["adiantamento_clientes"],
                inicio=i_pc or 0, fim=fim_pc,
            ),
            "provisoes": self._grupo(
                linhas, LABELS_BALANCO["provisoes"], inicio=i_pc or 0, fim=fim_pc
            ),
            "outras_obrigacoes": self._grupo(
                linhas, LABELS_BALANCO["outras_obrigacoes"],
                inicio=i_pc or 0, fim=fim_pc,
            ),
            "emprestimos": self._grupo(
                linhas, LABELS_BALANCO["emprestimos"], inicio=i_pc or 0, fim=fim_pc
            ),
            "total": self._valor(
                linhas, (SECTION_MARKERS["passivo_circulante"],), inicio=i_pc or 0
            ),
        }

        patrimonio = self._parse_patrimonio_liquido(linhas, inicio=i_pl or 0)

        return {
            "ativo": {
                "circulante": circulante,
                "nao_circulante": nao_circulante,
            },
            "passivo": {
                "circulante": passivo_circulante,
            },
            "patrimonio_liquido": patrimonio,
            "total_ativo": self._valor(linhas, LABELS_BALANCO["total_ativo"]),
            "total_passivo_pl": self._valor(linhas, LABELS_BALANCO["total_passivo_pl"]),
        }

    def _parse_imobilizado(
        self, linhas: list[ContaLinha], *, inicio: int, fim: int | None
    ) -> dict[str, Any] | None:
        """Separa os grupos de bens da depreciação acumulada."""
        linha = self._encontrar(
            linhas, LABELS_BALANCO["imobilizado"], inicio=inicio, fim=fim
        )
        if linha is None:
            return None

        filhos = self._filhos(linhas, linha)
        grupos: list[dict[str, Any]] = []
        depreciacao_total = 0.0
        tem_depreciacao = False

        for filho in filhos:
            if self._eh_depreciacao(filho.normalizada):
                depreciacao_total += abs(filho.valor)
                tem_depreciacao = True
                # Deprecição vinculada a um grupo já registrado (ex.: "(-) Depreciação Edifícios")
                alvo = self._grupo_correspondente(grupos, filho.normalizada)
                if alvo is not None:
                    alvo["depreciacao"] = abs(filho.valor)
                    alvo["liquido"] = round(alvo["custo"] - abs(filho.valor), 2)
                continue

            grupos.append(
                {
                    "nome": filho.descricao.strip(),
                    "custo": filho.valor,
                    "depreciacao": 0.0,
                    "liquido": filho.valor,
                }
            )

        return {
            "grupos": grupos,
            "depreciacao_total": round(depreciacao_total, 2) if tem_depreciacao else None,
            "total_liquido": linha.valor,
            "total_custo": round(sum(g["custo"] for g in grupos), 2) if grupos else None,
        }

    @staticmethod
    def _eh_depreciacao(descricao_normalizada: str) -> bool:
        return any(
            termo in descricao_normalizada
            for termo in ("DEPRECIAC", "AMORTIZAC", "EXAUSTAO")
        )

    @staticmethod
    def _grupo_correspondente(
        grupos: list[dict[str, Any]], descricao_normalizada: str
    ) -> dict[str, Any] | None:
        for grupo in grupos:
            nome = _normalizar(grupo["nome"])
            if nome and nome in descricao_normalizada:
                return grupo
        return None

    def _parse_intangivel(
        self, linhas: list[ContaLinha], *, inicio: int, fim: int | None
    ) -> dict[str, Any] | None:
        grupo = self._grupo(
            linhas, LABELS_BALANCO["intangivel"], inicio=inicio, fim=fim
        )
        if grupo is None or not grupo.get("total"):
            return None
        return grupo

    def _parse_patrimonio_liquido(
        self, linhas: list[ContaLinha], *, inicio: int
    ) -> dict[str, Any]:
        return {
            "capital_social": self._valor(
                linhas, LABELS_BALANCO["capital_social"], inicio=inicio
            ),
            "reservas": self._valor(
                linhas, LABELS_BALANCO["reservas"], inicio=inicio
            ),
            "ajustes": self._valor(linhas, LABELS_BALANCO["ajustes"], inicio=inicio),
            "total": self._valor(
                linhas, (SECTION_MARKERS["patrimonio_liquido"],), inicio=inicio
            ),
        }

    # ----------------------------------------------------------------- DRE

    def parse_dre(self, pdf_path: str) -> dict[str, Any]:
        texto = self.extract_text(pdf_path)
        return self.parse_dre_text(texto)

    def parse_dre_text(self, texto: str) -> dict[str, Any]:
        """Versão testável: recebe o texto já extraído do PDF."""
        linhas = self._parse_lines(texto)

        def v(chave: str) -> float | None:
            return self._valor(linhas, LABELS_DRE[chave])

        receitas_financeiras = v("receitas_financeiras")
        despesas_financeiras = v("despesas_financeiras")

        # A DRE do Domínio já traz o resultado financeiro apurado; só calculamos
        # quando essa linha não existe no relatório.
        liquido_financeiro = v("resultado_financeiro")
        if liquido_financeiro is None and (
            receitas_financeiras is not None or despesas_financeiras is not None
        ):
            liquido_financeiro = round(
                (receitas_financeiras or 0.0) - abs(despesas_financeiras or 0.0), 2
            )

        despesas_grupo = self._grupo(linhas, LABELS_DRE["despesas_operacionais"])

        return {
            "receita_bruta": v("receita_bruta"),
            "deducoes": v("deducoes"),
            "receita_liquida": v("receita_liquida"),
            "custos": {
                "custos_aplicados": v("custos_aplicados"),
                "mao_obra_direta": v("mao_obra_direta"),
            },
            "lucro_bruto": v("lucro_bruto"),
            "despesas_operacionais": {
                "total": v("despesas_operacionais"),
                "despesas_administrativas": v("despesas_administrativas"),
                "despesas_pessoal": v("despesas_pessoal"),
                "impostos_taxas": v("impostos_taxas"),
                "despesas_gerais": v("despesas_gerais"),
                "depreciacoes": v("depreciacoes"),
                "servicos_terceiros": v("servicos_terceiros"),
                "itens": despesas_grupo["itens"] if despesas_grupo else [],
            },
            "resultado_financeiro": {
                "receitas_financeiras": receitas_financeiras,
                "despesas_financeiras": despesas_financeiras,
                "liquido": liquido_financeiro,
            },
            "outras_receitas": v("outras_receitas"),
            "resultado_operacional": v("resultado_operacional"),
            "lucro_liquido": v("lucro_liquido"),
        }
