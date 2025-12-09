from decimal import Decimal

from domain import (
    analisar_calendario,
    Configuracao,
    gerar_projecao,
    load_data,
    OrcamentoData,
    GastoFixo,
    Parcelamento
)

def test_config_values_from_file() -> None:
    """Verifies that the configuration loads the correct VA and VT values from the file."""
    # We load the actual file to verify it was updated correctly
    data = load_data("orcamento.json")
    assert data.configuracao.valor_diario_va == Decimal("30.0")
    assert data.configuracao.valor_diario_vt == Decimal("12.0")

def test_benefit_calculation_logic() -> None:
    """Verifies that benefits are added to net salary without being affected by taxes (since they are non-taxable in this domain)."""
    vt = Decimal("12.0")
    va = Decimal("30.0")

    # Configuration with benefits
    config_with_benefits = Configuracao(
        salario_base=Decimal("2000.00"),
        produtividade_media=Decimal("0.00"),
        meta_investimento_percentual=Decimal("0.0"),
        estado_feriados="SP",
        valor_diario_vt=vt,
        valor_diario_va=va
    )

    # Configuration without benefits
    config_no_benefits = Configuracao(
        salario_base=Decimal("2000.00"),
        produtividade_media=Decimal("0.00"),
        meta_investimento_percentual=Decimal("0.0"),
        estado_feriados="SP",
        valor_diario_vt=Decimal("0.0"),
        valor_diario_va=Decimal("0.0")
    )

    gastos: list[GastoFixo] = []
    parc: list[Parcelamento] = []

    # Generate projection with benefits
    data_with = OrcamentoData(config_with_benefits, gastos, parc)
    proj_with = gerar_projecao(data_with, meses=1)[0]

    # Generate projection without benefits
    data_no = OrcamentoData(config_no_benefits, gastos, parc)
    proj_no = gerar_projecao(data_no, meses=1)[0]

    # Calculate expected benefits manually
    _, _, uteis_beneficios = analisar_calendario(proj_with.data.year, proj_with.data.month, "SP")
    total_beneficios = (vt + va) * uteis_beneficios

    # The difference in net salary should be exactly the total benefits
    # This verifies benefits are added directly to net salary and do not affect taxes (or are added after taxes)
    assert proj_with.salario_liquido - proj_no.salario_liquido == total_beneficios
