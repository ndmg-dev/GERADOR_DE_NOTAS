"""Testes do parser com texto mockado no padrão dos PDFs do sistema Domínio."""

import pytest

from app.services.pdf_parser import PdfParserService

BALANCO_TEXTO = """
                    BALANÇO PATRIMONIAL
CNPJ: 12.345.678/0001-90
Período: 01/01/2025 a 31/12/2025

Descrição                                        Saldo Atual
ATIVO                                          1.566.336,51D
  ATIVO CIRCULANTE                               815.540,60D
    CAIXA E EQUIVALENTE DE CAIXA                 315.540,60D
      Caixa Geral                                  5.200,10D
      Banco do Brasil S/A                        180.340,50D
      Aplicações de Liquidez Imediata            130.000,00D
    CLIENTES                                     400.000,00D
      Duplicatas a Receber                       420.000,00D
      (-) Perdas Estimadas                        20.000,00C
    OUTROS CRÉDITOS                              100.000,00D
      Adiantamentos a Fornecedores                60.000,00D
      Impostos a Recuperar                        40.000,00D
  ATIVO NÃO-CIRCULANTE                           750.795,91D
    REALIZÁVEL A LONGO PRAZO                      50.000,00D
      Depósitos Judiciais                         50.000,00D
    IMOBILIZADO                                  680.795,91D
      Edifícios                                  500.000,00D
      Máquinas e Equipamentos                    250.000,00D
      Veículos                                   120.000,00D
      (-) Depreciação Acumulada Edifícios        100.000,00C
      (-) Depreciação Acumulada Veículos          89.204,09C
    INTANGÍVEL                                    20.000,00D
      Software de Gestão                          20.000,00D

PASSIVO                                        1.566.336,51C
  PASSIVO CIRCULANTE                             800.967,11C
    FORNECEDORES                                 300.000,00C
      Fornecedores Nacionais                     300.000,00C
    OBRIGAÇÕES TRIBUTÁRIAS                       150.967,11C
      ISS a Recolher                              50.967,11C
      IRPJ a Recolher                            100.000,00C
    OBRIGAÇÕES TRABALHISTAS                      250.000,00C
      Salários a Pagar                           150.000,00C
      FGTS a Recolher                            100.000,00C
    OUTRAS OBRIGAÇÕES                            100.000,00C
      Contas a Pagar                             100.000,00C
  PATRIMÔNIO LÍQUIDO                             765.369,40C
    CAPITAL SOCIAL                               500.000,00C
    RESERVAS DE LUCROS                           250.000,00C
    AJUSTES DE AVALIAÇÃO PATRIMONIAL              15.369,40C

TOTAL DO ATIVO                                 1.566.336,51D
TOTAL DO PASSIVO E PATRIMÔNIO LÍQUIDO          1.566.336,51C
"""

DRE_TEXTO = """
              DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO
Descrição                                        Saldo Atual

RECEITA OPERACIONAL BRUTA                      2.000.000,00C
DEDUÇÕES DA RECEITA BRUTA                        200.000,00D
RECEITA OPERACIONAL LÍQUIDA                    1.800.000,00C
CUSTOS APLICADOS                                 900.000,00D
  Mão de Obra Direta                             400.000,00D
LUCRO BRUTO                                      900.000,00C
DESPESAS OPERACIONAIS                            500.000,00D
  DESPESAS COM PESSOAL                           300.000,00D
  IMPOSTOS TAXAS E CONTRIBUIÇÕES                  50.000,00D
  DESPESAS GERAIS                                150.000,00D
RECEITAS FINANCEIRAS                              30.000,00C
DESPESAS FINANCEIRAS                              10.000,00D
OUTRAS RECEITAS                                   20.000,00C
RESULTADO OPERACIONAL                            440.000,00C
LUCRO LÍQUIDO DO EXERCÍCIO                       440.000,00C
"""


@pytest.fixture
def parser() -> PdfParserService:
    return PdfParserService()


# ------------------------------------------------------------------ _parse_value


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("1.566.336,51D", 1566336.51),
        ("800.967,11C", -800967.11),
        ("315.540,60D", 315540.60),
        ("1.111,11D", 1111.11),
        ("222,22C", -222.22),
        ("0,00D", 0.0),
        ("(1.000,00)", -1000.00),
        ("-500,00", -500.00),
        ("1.566.336,51", 1566336.51),
    ],
)
def test_parse_value(parser: PdfParserService, entrada: str, esperado: float) -> None:
    assert parser._parse_value(entrada) == pytest.approx(esperado)


@pytest.mark.parametrize("entrada", ["", "   ", "abc", None, "ATIVO CIRCULANTE"])
def test_parse_value_invalido_retorna_none(parser: PdfParserService, entrada) -> None:
    assert parser._parse_value(entrada) is None


# ---------------------------------------------------------------- parse_balanco


def test_balanco_caixa_equivalentes(parser: PdfParserService) -> None:
    balanco = parser.parse_balanco_text(BALANCO_TEXTO)
    caixa = balanco["ativo"]["circulante"]["caixa_equivalentes"]

    assert caixa["total"] == pytest.approx(315540.60)
    assert len(caixa["itens"]) == 3
    assert caixa["itens"][0]["descricao"] == "Caixa Geral"
    assert caixa["itens"][1]["valor"] == pytest.approx(180340.50)


def test_balanco_clientes_com_conta_credora(parser: PdfParserService) -> None:
    balanco = parser.parse_balanco_text(BALANCO_TEXTO)
    clientes = balanco["ativo"]["circulante"]["clientes"]

    assert clientes["total"] == pytest.approx(400000.00)
    # "(-) Perdas Estimadas 20.000,00C" deve virar valor negativo
    assert clientes["itens"][1]["valor"] == pytest.approx(-20000.00)


def test_balanco_imobilizado_separa_depreciacao(parser: PdfParserService) -> None:
    balanco = parser.parse_balanco_text(BALANCO_TEXTO)
    imob = balanco["ativo"]["nao_circulante"]["imobilizado"]

    nomes = [g["nome"] for g in imob["grupos"]]
    assert nomes == ["Edifícios", "Máquinas e Equipamentos", "Veículos"]
    assert imob["depreciacao_total"] == pytest.approx(189204.09)
    assert imob["total_liquido"] == pytest.approx(680795.91)
    assert imob["total_custo"] == pytest.approx(870000.00)

    edificios = imob["grupos"][0]
    assert edificios["depreciacao"] == pytest.approx(100000.00)
    assert edificios["liquido"] == pytest.approx(400000.00)


def test_balanco_passivo_e_patrimonio(parser: PdfParserService) -> None:
    balanco = parser.parse_balanco_text(BALANCO_TEXTO)
    pc = balanco["passivo"]["circulante"]
    pl = balanco["patrimonio_liquido"]

    assert pc["fornecedores"]["total"] == pytest.approx(-300000.00)
    assert pc["obrigacoes_fiscais"]["total"] == pytest.approx(-150967.11)
    assert len(pc["obrigacoes_trabalhistas"]["itens"]) == 2
    assert pl["capital_social"] == pytest.approx(-500000.00)
    assert pl["total"] == pytest.approx(-765369.40)


def test_balanco_totais(parser: PdfParserService) -> None:
    balanco = parser.parse_balanco_text(BALANCO_TEXTO)
    assert balanco["total_ativo"] == pytest.approx(1566336.51)
    assert balanco["total_passivo_pl"] == pytest.approx(-1566336.51)


def test_balanco_intangivel_ausente_retorna_none(parser: PdfParserService) -> None:
    texto = BALANCO_TEXTO.replace("    INTANGÍVEL                                    20.000,00D", "")
    balanco = parser.parse_balanco_text(texto)
    assert balanco["ativo"]["nao_circulante"]["intangivel"] is None


def test_balanco_tolerante_a_conta_ausente(parser: PdfParserService) -> None:
    """Conta inexistente vira None, sem lançar exceção."""
    balanco = parser.parse_balanco_text("Descrição   Saldo Atual\nATIVO   0,00D\n")

    assert balanco["ativo"]["circulante"]["caixa_equivalentes"] is None
    assert balanco["ativo"]["nao_circulante"]["imobilizado"] is None
    assert balanco["patrimonio_liquido"]["capital_social"] is None


def test_balanco_texto_vazio_nao_lanca(parser: PdfParserService) -> None:
    balanco = parser.parse_balanco_text("")
    assert balanco["total_ativo"] is None
    assert balanco["passivo"]["circulante"]["fornecedores"] is None


# -------------------------------------------------------------------- parse_dre


def test_dre_valores_principais(parser: PdfParserService) -> None:
    dre = parser.parse_dre_text(DRE_TEXTO)

    assert dre["receita_bruta"] == pytest.approx(-2000000.00)
    assert dre["deducoes"] == pytest.approx(200000.00)
    assert dre["receita_liquida"] == pytest.approx(-1800000.00)
    assert dre["lucro_bruto"] == pytest.approx(-900000.00)
    assert dre["lucro_liquido"] == pytest.approx(-440000.00)


def test_dre_custos_e_despesas(parser: PdfParserService) -> None:
    dre = parser.parse_dre_text(DRE_TEXTO)

    assert dre["custos"]["custos_aplicados"] == pytest.approx(900000.00)
    assert dre["custos"]["mao_obra_direta"] == pytest.approx(400000.00)
    assert dre["despesas_operacionais"]["total"] == pytest.approx(500000.00)
    assert dre["despesas_operacionais"]["despesas_pessoal"] == pytest.approx(300000.00)
    assert dre["despesas_operacionais"]["impostos_taxas"] == pytest.approx(50000.00)
    assert dre["despesas_operacionais"]["despesas_gerais"] == pytest.approx(150000.00)
    assert len(dre["despesas_operacionais"]["itens"]) == 3


def test_dre_resultado_financeiro(parser: PdfParserService) -> None:
    dre = parser.parse_dre_text(DRE_TEXTO)
    rf = dre["resultado_financeiro"]

    assert rf["receitas_financeiras"] == pytest.approx(-30000.00)
    assert rf["despesas_financeiras"] == pytest.approx(10000.00)
    assert rf["liquido"] == pytest.approx(-40000.00)


def test_dre_tolerante_a_campos_ausentes(parser: PdfParserService) -> None:
    dre = parser.parse_dre_text("Descrição   Saldo Atual\nRECEITA BRUTA   100,00C\n")

    assert dre["receita_bruta"] == pytest.approx(-100.00)
    assert dre["lucro_liquido"] is None
    assert dre["custos"]["custos_aplicados"] is None
    assert dre["resultado_financeiro"]["liquido"] is None


# ----------------------------------------- hierarquia reconstruída por soma

# Nos PDFs reais do Domínio a extração perde a indentação dos níveis mais
# profundos: contas sintéticas e analíticas saem na mesma coluna. A hierarquia
# precisa ser reconstruída pela aritmética (sintética = soma das analíticas).
BALANCO_ACHATADO = """
Descricao                                        Saldo Atual
ATIVO                                          1.000.000,00D
  ATIVO CIRCULANTE                               315.540,60D
   CAIXA E EQUIVALENTE DE CAIXA                  315.540,60D
    CAIXA                                         38.594,72D
    CAIXA GERAL                                   38.594,72D
    BANCOS CONTA MOVIMENTO                        35.539,97D
    CAIXA ECONOMICA FEDERAL C/C 3940-2            24.714,58D
    BANCO SANTANDER AG 2371                            1,01D
    BANCO SANTANDER AG 3029                       10.824,38D
    APLICACOES FINANCEIRAS LIQUIDEZ IMEDIATA     241.405,91D
    APLICACAO CAIXA ECONOMICA FEDERAL             63.244,88D
    APLICACAO SANTANDER                          178.161,03D
"""


def test_hierarquia_achatada_lista_apenas_primeiro_nivel(
    parser: PdfParserService,
) -> None:
    balanco = parser.parse_balanco_text(BALANCO_ACHATADO)
    caixa = balanco["ativo"]["circulante"]["caixa_equivalentes"]

    descricoes = [item["descricao"] for item in caixa["itens"]]
    assert descricoes == [
        "CAIXA",
        "BANCOS CONTA MOVIMENTO",
        "APLICACOES FINANCEIRAS LIQUIDEZ IMEDIATA",
    ]


def test_hierarquia_achatada_itens_somam_o_total(parser: PdfParserService) -> None:
    """Sem a reconstrução, as analíticas dobrariam o total."""
    balanco = parser.parse_balanco_text(BALANCO_ACHATADO)
    caixa = balanco["ativo"]["circulante"]["caixa_equivalentes"]

    soma = sum(item["valor"] for item in caixa["itens"])
    assert soma == pytest.approx(caixa["total"])
    assert soma == pytest.approx(315540.60)


def test_agrupar_por_soma_mantem_folhas_independentes(
    parser: PdfParserService,
) -> None:
    """Contas que não somam entre si permanecem todas no mesmo nível."""
    texto = """
Descricao                       Saldo Atual
ATIVO                            1.000,00D
  ATIVO CIRCULANTE                 600,00D
   CAIXA E EQUIVALENTE DE CAIXA    600,00D
    CONTA A                        100,00D
    CONTA B                        200,00D
    CONTA C                        300,00D
"""
    caixa = parser.parse_balanco_text(texto)["ativo"]["circulante"][
        "caixa_equivalentes"
    ]
    assert [i["descricao"] for i in caixa["itens"]] == ["CONTA A", "CONTA B", "CONTA C"]


def test_subgrupo_recupera_analiticas_do_mesmo_nivel(
    parser: PdfParserService,
) -> None:
    """Subgrupo cujas analíticas saíram no mesmo recuo que ele.

    É o caso de PROVISÕES dentro de OBRIGAÇÕES TRABALHISTAS no balanço real.
    """
    texto = """
Descricao                                       Saldo Atual
PASSIVO                                        1.000.000,00C
  PASSIVO CIRCULANTE                             900.000,00C
   OBRIGACOES TRABALHISTA E PREVIDENCIARIA       900.000,00C
    OBRIGACOES COM O PESSOAL                     300.000,00C
    OBRIGACOES SOCIAIS                           200.000,00C
    PROVISOES                                    400.000,00C
    PROVISOES PARA FERIAS                        250.000,00C
    INSS SOBRE PROVISOES PARA FERIAS             100.000,00C
    FGTS SOBRE PROVISOES PARA FERIAS              50.000,00C
"""
    pc = parser.parse_balanco_text(texto)["passivo"]["circulante"]

    trabalhistas = pc["obrigacoes_trabalhistas"]
    assert [i["descricao"] for i in trabalhistas["itens"]] == [
        "OBRIGACOES COM O PESSOAL",
        "OBRIGACOES SOCIAIS",
        "PROVISOES",
    ]

    provisoes = pc["provisoes"]
    assert provisoes["total"] == pytest.approx(-400000.00)
    assert [i["descricao"] for i in provisoes["itens"]] == [
        "PROVISOES PARA FERIAS",
        "INSS SOBRE PROVISOES PARA FERIAS",
        "FGTS SOBRE PROVISOES PARA FERIAS",
    ]


def test_depreciacao_nao_e_contada_em_dobro(parser: PdfParserService) -> None:
    """A sintética de depreciação não pode somar com suas analíticas."""
    texto = """
Descricao                                    Saldo Atual
ATIVO                                        1.000.000,00D
  ATIVO NAO-CIRCULANTE                         835.775,38D
   IMOBILIZADO                                 835.775,38D
    EDIFICIOS                                  500.000,00D
    MAQUINAS                                   400.000,00D
    (-) DEPRECIACOES ACUMULADAS                 64.224,62C
    (-) DEPRECIACAO DE EDIFICIOS                24.224,62C
    (-) DEPRECIACAO DE MAQUINAS                 40.000,00C
"""
    imob = parser.parse_balanco_text(texto)["ativo"]["nao_circulante"]["imobilizado"]

    assert imob["depreciacao_total"] == pytest.approx(64224.62)
    assert imob["total_custo"] == pytest.approx(900000.00)
    assert imob["total_custo"] - imob["depreciacao_total"] == pytest.approx(
        imob["total_liquido"]
    )


# ------------------------------------------------- detect_extraction_method


def test_detect_extraction_method_pdf_invalido(
    parser: PdfParserService, tmp_path
) -> None:
    """PDF corrompido/ilegível cai para OCR em vez de lançar exceção."""
    arquivo = tmp_path / "corrompido.pdf"
    arquivo.write_bytes(b"%PDF-1.4 lixo")

    assert parser.detect_extraction_method(str(arquivo)) == "ocr"
