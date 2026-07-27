"""Testes do construtor de notas."""

import pytest

from app.services.notas_builder import NotasBuilderService, Tabela, formatar_brl
from app.services.pdf_parser import PdfParserService
from tests.test_pdf_parser import BALANCO_TEXTO, DRE_TEXTO

EMPRESA = {
    "nome": "Soberana Serviços Ltda.",
    "cnpj": "12.345.678/0001-90",
    "endereco": "Rua das Acácias, 100 — Goiânia/GO",
    "socios": [
        {
            "nome": "Albert Mario da Silva",
            "cpf": "657.123.456-00",
            "participacao": "R$ 250.000,00",
            "cargo": "Sócio Administrador",
        },
        {
            "nome": "Maria Helena Souza",
            "cpf": "123.456.789-00",
            "participacao": "R$ 250.000,00",
            "cargo": "Sócia",
        },
    ],
    "contador_nome": "Siler Rodrigues",
    "contador_crc": "GO-012345/O-1",
    "contador_cpf": "987.654.321-00",
}

CONFIG = {"ano": 2025, "data_aprovacao": "20 de julho de 2026"}


@pytest.fixture
def notas():
    parser = PdfParserService()
    balanco = parser.parse_balanco_text(BALANCO_TEXTO)
    dre = parser.parse_dre_text(DRE_TEXTO)
    return NotasBuilderService().build_all(balanco, dre, EMPRESA, CONFIG)


def test_formatar_brl() -> None:
    assert formatar_brl(1566336.51) == "1.566.336,51"
    assert formatar_brl(-800967.11) == "-800.967,11"
    assert formatar_brl(0) == "0,00"
    assert formatar_brl(None) == "-"


def test_build_all_gera_vinte_notas(notas) -> None:
    assert len(notas) == 20
    assert [n.numero for n in notas] == list(range(1, 21))


def test_placeholders_resolvidos(notas) -> None:
    texto = notas[0].conteudo[0].texto
    assert "Soberana Serviços Ltda." in texto
    assert "12.345.678/0001-90" in texto
    assert "{empresa.nome}" not in texto

    aprovacao = " ".join(b.texto for b in notas[19].conteudo)
    assert "20 de julho de 2026" in aprovacao
    assert "2025" in aprovacao


def test_nota_caixa_traz_itens_e_total(notas) -> None:
    caixa = next(n for n in notas if n.titulo == "Caixa e Equivalentes de Caixa")
    tabela = next(b for b in caixa.conteudo if isinstance(b, Tabela))

    assert tabela.colunas == ["Descrição", "2025"]
    assert len(tabela.linhas) == 3
    assert tabela.total == ["Total", "315.540,60"]


def test_nota_imobilizado_tem_quatro_colunas(notas) -> None:
    imob = next(n for n in notas if n.titulo == "Imobilizado")
    tabela = next(b for b in imob.conteudo if isinstance(b, Tabela))

    assert tabela.colunas == [
        "Descrição",
        "Custo",
        "Depreciação Acumulada",
        "Valor Líquido",
    ]
    assert tabela.total == ["Total", "870.000,00", "-189.204,09", "680.795,91"]


def test_notas_de_passivo_usam_valores_positivos(notas) -> None:
    fornecedores = next(n for n in notas if n.titulo == "Fornecedores")
    tabela = next(b for b in fornecedores.conteudo if isinstance(b, Tabela))
    assert tabela.total == ["Total", "300.000,00"]


def test_nota_capital_social_lista_socios(notas) -> None:
    capital = next(n for n in notas if n.titulo == "Capital Social")
    tabela = next(b for b in capital.conteudo if isinstance(b, Tabela))

    assert tabela.colunas == ["Sócio", "CPF", "Participação"]
    assert tabela.linhas[0][0] == "Albert Mario da Silva"
    assert tabela.total == ["Total", "", "500.000,00"]


def test_notas_sem_dados_sao_omitidas() -> None:
    """Balanço e DRE vazios deixam apenas as notas puramente textuais."""
    builder = NotasBuilderService()
    notas = builder.build_all({}, {}, EMPRESA, CONFIG)

    titulos = [n.titulo for n in notas]
    assert "Caixa e Equivalentes de Caixa" not in titulos
    assert "Imobilizado" not in titulos
    assert "Contexto Operacional" in titulos
    assert [n.numero for n in notas] == list(range(1, len(notas) + 1))


def test_intangivel_omitido_quando_zerado() -> None:
    parser = PdfParserService()
    texto = BALANCO_TEXTO.replace("20.000,00D", "0,00D")
    balanco = parser.parse_balanco_text(texto)
    dre = parser.parse_dre_text(DRE_TEXTO)

    notas = NotasBuilderService().build_all(balanco, dre, EMPRESA, CONFIG)
    assert "Intangível" not in [n.titulo for n in notas]
