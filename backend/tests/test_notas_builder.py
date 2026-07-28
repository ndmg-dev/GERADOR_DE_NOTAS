"""Testes do construtor de notas (estrutura do modelo de referência)."""

import pytest

from app.services.notas_builder import NotasBuilderService, Tabela, formatar_brl
from app.services.pdf_parser import PdfParserService
from tests.test_pdf_parser import BALANCO_TEXTO, DRE_TEXTO

# Dados fictícios. Nenhum dado real de cliente entra nos testes: o repositório
# é versionado e CPF é dado pessoal.
EMPRESA = {
    "nome": "Instituição de Ensino Exemplo Ltda",
    "cnpj": "11.222.333/0001-81",
    "endereco": "Avenida das Palmeiras, 1000 — Cidade Exemplo/UF",
    "socios": [
        {
            "nome": "Ana Paula Ribeiro de Souza",
            "cpf": "111.444.777-35",
            "participacao": "R$ 50.000,00",
            "cargo": "REPRESENTANTE LEGAL",
        },
        {
            "nome": "Carlos Eduardo Nunes",
            "cpf": "222.333.444-05",
            "participacao": "R$ 50.000,00",
            "cargo": "REPRESENTANTE LEGAL",
        },
    ],
    "contador_nome": "Marina Alves Pereira",
    "contador_crc": "UF000000/O-0",
    "contador_cpf": "333.444.555-96",
}

CONFIG = {"ano": 2025, "data_aprovacao": "20 de julho de 2026"}

# Títulos das 20 notas do modelo de referência, na ordem.
TITULOS_REFERENCIA = [
    "Contexto operacional",
    "Apresentação das Demonstrações Contábeis",
    "Sumário das principais práticas contábeis",
    "Caixa e equivalentes de Caixa",
    "Contas a receber de clientes",
    "Créditos",
    "Realizável a Longo Prazo",
    "Imobilizado",
    "Fornecedores",
    "Empréstimos e Financiamentos",
    "Obrigações Trabalhistas",
    "Obrigações Fiscais",
    "Adiantamento de Clientes",
    "Outras Obrigações",
    "Provisões",
    "Capital Social",
    "Receita Operacional Líquida",
    "Informações sobre a Natureza das Despesas e Custos",
    "Resultado Financeiro",
    "Aprovação das Demonstrações Financeiras",
]


def _exercicio(ano: int, balanco_texto: str, dre_texto: str) -> dict:
    parser = PdfParserService()
    return {
        "ano": ano,
        "balanco": parser.parse_balanco_text(balanco_texto),
        "dre": parser.parse_dre_text(dre_texto),
    }


@pytest.fixture
def notas():
    return NotasBuilderService().build_all(
        [_exercicio(2025, BALANCO_TEXTO, DRE_TEXTO)], EMPRESA, CONFIG
    )


@pytest.fixture
def notas_comparativas():
    return NotasBuilderService().build_all(
        [
            _exercicio(2025, BALANCO_TEXTO, DRE_TEXTO),
            _exercicio(2024, BALANCO_TEXTO, DRE_TEXTO),
            _exercicio(2023, BALANCO_TEXTO, DRE_TEXTO),
        ],
        EMPRESA,
        CONFIG,
    )


def _tabela(nota) -> Tabela:
    return next(b for b in nota.conteudo if isinstance(b, Tabela))


def _por_titulo(notas, titulo):
    return next(n for n in notas if n.titulo == titulo)


def test_formatar_brl() -> None:
    assert formatar_brl(1566336.51) == "1.566.336,51"
    assert formatar_brl(-800967.11) == "-800.967,11"
    assert formatar_brl(0) == "0,00"
    assert formatar_brl(None) == "0,00"


def test_ordem_das_notas_segue_o_modelo(notas) -> None:
    titulos = [n.titulo for n in notas]
    # As notas presentes devem aparecer na mesma ordem relativa do modelo.
    posicoes = [TITULOS_REFERENCIA.index(t) for t in titulos]
    assert posicoes == sorted(posicoes)
    assert [n.numero for n in notas] == list(range(1, len(notas) + 1))


def test_notas_do_modelo_ausentes_no_builder() -> None:
    """Todo título gerado precisa existir no modelo de referência."""
    notas = NotasBuilderService().build_all(
        [_exercicio(2025, BALANCO_TEXTO, DRE_TEXTO)], EMPRESA, CONFIG
    )
    for nota in notas:
        assert nota.titulo in TITULOS_REFERENCIA


def test_placeholders_resolvidos(notas) -> None:
    texto = notas[0].conteudo[0].texto
    assert EMPRESA["nome"] in texto
    assert EMPRESA["cnpj"] in texto
    assert "{empresa.nome}" not in texto

    aprovacao = " ".join(
        b.texto for b in _por_titulo(notas, TITULOS_REFERENCIA[19]).conteudo
    )
    assert "20 de julho de 2026" in aprovacao


def test_nota_caixa_lista_apenas_primeiro_nivel(notas) -> None:
    tabela = _tabela(_por_titulo(notas, "Caixa e equivalentes de Caixa"))

    assert tabela.colunas == ["Descrição", "2025"]
    assert tabela.total == ["Total", "315.540,60"]
    soma = sum(float(l[1].replace(".", "").replace(",", ".")) for l in tabela.linhas)
    assert soma == pytest.approx(315540.60)


def test_tabelas_comparativas_tres_exercicios(notas_comparativas) -> None:
    tabela = _tabela(_por_titulo(notas_comparativas, "Caixa e equivalentes de Caixa"))

    assert tabela.colunas == ["Descrição", "2025", "2024", "2023"]
    assert tabela.total == ["Total", "315.540,60", "315.540,60", "315.540,60"]
    for linha in tabela.linhas:
        assert len(linha) == 4


def test_nota_imobilizado_e_tabela_de_movimentacao(notas_comparativas) -> None:
    tabela = _tabela(_por_titulo(notas_comparativas, "Imobilizado"))

    assert tabela.colunas == [
        "Imobilizado/Intangível",
        "Saldo 2024",
        "Aquisições",
        "Baixas",
        "Depreciação",
        "Saldo 2025",
    ]
    assert tabela.total[0] == "Total Imobilizado"
    assert any(l[0] == "(-) Depreciação Acumulada" for l in tabela.linhas)


def test_movimentacao_imobilizado_padrao_vem_zerada() -> None:
    from app.services.notas_builder import movimentacao_imobilizado_padrao

    balanco = PdfParserService().parse_balanco_text(BALANCO_TEXTO)
    movimentacao = movimentacao_imobilizado_padrao(balanco)

    assert "EDIFICIOS" in movimentacao
    assert "DEPRECIACAO ACUMULADA" in movimentacao
    assert movimentacao["EDIFICIOS"]["aquisicoes"] == 0.0
    assert movimentacao["EDIFICIOS"]["rotulo"] == "Edifícios"


def test_nota_imobilizado_usa_movimentacao_revisada() -> None:
    """Aquisições, baixas e depreciação digitadas na revisão entram na Nota 08."""
    from app.services.notas_builder import movimentacao_imobilizado_padrao

    exercicio = _exercicio(2025, BALANCO_TEXTO, DRE_TEXTO)
    movimentacao = movimentacao_imobilizado_padrao(exercicio["balanco"])
    movimentacao["EDIFICIOS"].update({"aquisicoes": 10_000.00, "baixas": 2_500.00})
    movimentacao["DEPRECIACAO ACUMULADA"]["depreciacao"] = 7_000.00
    exercicio["movimentacao_imobilizado"] = movimentacao

    notas = NotasBuilderService().build_all([exercicio], EMPRESA, CONFIG)
    tabela = _tabela(_por_titulo(notas, "Imobilizado"))

    edificios = next(l for l in tabela.linhas if l[0] == "Edifícios")
    assert edificios[2] == "10.000,00"  # aquisições
    assert edificios[3] == "2.500,00"  # baixas

    depreciacao = next(l for l in tabela.linhas if l[0].startswith("(-) Deprecia"))
    assert depreciacao[4] == "-7.000,00"

    # A linha de total soma as colunas de movimentação.
    assert tabela.total[2] == "10.000,00"
    assert tabela.total[3] == "2.500,00"
    assert tabela.total[4] == "-7.000,00"


def test_notas_de_passivo_usam_valores_positivos(notas) -> None:
    tabela = _tabela(_por_titulo(notas, "Fornecedores"))
    assert tabela.total == ["Total", "300.000,00"]


def test_nota_capital_social_sem_cpf_no_quadro(notas) -> None:
    """O modelo traz apenas nome e participação no quadro societário."""
    tabela = _tabela(_por_titulo(notas, "Capital Social"))

    assert tabela.colunas == ["Sócio", "Participação"]
    assert tabela.linhas[0][0] == EMPRESA["socios"][0]["nome"]
    assert tabela.total == ["Total", "R$ 500.000,00"]


def test_nota_natureza_despesas_e_matriz(notas) -> None:
    tabela = _tabela(_por_titulo(notas, "Informações sobre a Natureza das Despesas e Custos"))

    assert tabela.colunas == [
        "Natureza dos Custos e Despesas",
        "Custos",
        "Despesas Gerais e Administrativas",
        "Total",
    ]
    assert [l[0] for l in tabela.linhas] == [
        "Custo do Serviço Prestado",
        "Serviços de Terceiros",
        "Depreciações",
        "Outros Custos e Despesas",
    ]


def test_nota_natureza_despesas_aceita_valores_revisados() -> None:
    """A abertura por natureza digitada na revisão substitui o padrão."""
    exercicio = _exercicio(2025, BALANCO_TEXTO, DRE_TEXTO)
    exercicio["natureza_despesas"] = {
        "custo_servico": 1_000.00,
        "servicos_terceiros": 200.00,
        "depreciacoes": 300.00,
        "outros": 500.00,
    }

    notas = NotasBuilderService().build_all([exercicio], EMPRESA, CONFIG)
    tabela = _tabela(
        _por_titulo(notas, "Informações sobre a Natureza das Despesas e Custos")
    )

    assert tabela.linhas[0] == ["Custo do Serviço Prestado", "1.000,00", "0,00", "1.000,00"]
    assert tabela.linhas[1] == ["Serviços de Terceiros", "0,00", "200,00", "200,00"]
    assert tabela.total == ["Total", "1.000,00", "1.000,00", "2.000,00"]


def test_natureza_despesas_padrao_usa_a_dre() -> None:
    from app.services.notas_builder import natureza_despesas_padrao

    dre = PdfParserService().parse_dre_text(DRE_TEXTO)
    padrao = natureza_despesas_padrao(dre)

    # custos aplicados (900.000) + mão de obra direta (400.000)
    assert padrao["custo_servico"] == pytest.approx(1_300_000.00)
    # o Domínio não abre estes na DRE
    assert padrao["servicos_terceiros"] == 0.0
    assert padrao["depreciacoes"] == 0.0
    # o restante das despesas operacionais
    assert padrao["outros"] == pytest.approx(500_000.00)


def test_nota_resultado_financeiro(notas) -> None:
    tabela = _tabela(_por_titulo(notas, "Resultado Financeiro"))
    assert [l[0] for l in tabela.linhas] == [
        "Receitas Financeiras",
        "Outras Despesas Financeiras",
    ]


def test_notas_sem_dados_sao_omitidas() -> None:
    notas = NotasBuilderService().build_all(
        [{"ano": 2025, "balanco": {}, "dre": {}}], EMPRESA, CONFIG
    )
    titulos = [n.titulo for n in notas]

    assert "Caixa e equivalentes de Caixa" not in titulos
    assert "Imobilizado" not in titulos
    assert "Contexto operacional" in titulos
    assert [n.numero for n in notas] == list(range(1, len(notas) + 1))


def test_sem_exercicios_nao_lanca() -> None:
    notas = NotasBuilderService().build_all([], EMPRESA, CONFIG)
    assert [n.titulo for n in notas] == [
        "Contexto operacional",
        "Apresentação das Demonstrações Contábeis",
        "Sumário das principais práticas contábeis",
        "Aprovação das Demonstrações Financeiras",
    ]
