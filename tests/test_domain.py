import datetime
import json
from decimal import Decimal
from unittest.mock import patch, mock_open


from domain import (
    analisar_calendario,
    calcular_inss,
    calcular_irrf,
    Parcelamento,
    Configuracao,
    calcular_holerite,
    gerar_projecao,
    load_data,
    OrcamentoData,
    GastoFixo,
)

def test_analisar_calendario_sp_july_2024() -> None:
    # July 2024 in SP
    # 1st is Monday
    # 31 days total
    # Sundays: 7, 14, 21, 28 (4 days)
    # Holidays: July 9 (Tuesday) - Revolução Constitucionalista (State Holiday)
    # Total Rest Days: 4 + 1 = 5
    # Total Work Days: 31 - 5 = 26

    uteis, descanso, uteis_beneficios = analisar_calendario(2024, 7, "SP")
    assert descanso == 5
    assert uteis == 26
    # July 2024:
    # 1st is Mon. 31 days.
    # Sats: 6, 13, 20, 27 (4 days)
    # Suns: 7, 14, 21, 28 (4 days)
    # Holiday: July 9 (Tue)
    # Weekdays (Mon-Fri) = 31 - 4(Sat) - 4(Sun) = 23.
    # Minus Holiday (Tue 9) = 22.
    assert uteis_beneficios == 22

def test_analisar_calendario_april_2024_overlap() -> None:
    # April 2024
    # 21 (Sunday) - Tiradentes (National Holiday)
    # Sundays: 7, 14, 21, 28 (4 days)
    # The holiday falls on a Sunday.
    # Logic: is_sunday OR is_holiday.
    # So day 21 counts as 1 rest day.
    # Total rest days: 4.
    # Total days: 30.
    # Work days: 26.

    uteis, descanso, uteis_beneficios = analisar_calendario(2024, 4, "SP")
    assert descanso == 4
    assert uteis == 26
    # April 2024
    # 30 days.
    # Suns: 7, 14, 21, 28 (4) -> 21 is also holiday.
    # Sats: 6, 13, 20, 27 (4)
    # Weekdays (Mon-Fri) = 30 - 4 - 4 = 22.
    # No other holidays in April 2024 (Tiradentes is on Sun).
    # Wait, May 1st is close, but April only.
    # So 22.
    assert uteis_beneficios == 22

def test_calcular_inss() -> None:
    # Based on 2024 table in code

    # 1. Below first bracket (<= 1412.00) -> 7.5%
    val = Decimal("1000.00")
    expected = val * Decimal("0.075")
    assert calcular_inss(val) == expected

    # 2. Top of first bracket (1412.00)
    val = Decimal("1412.00")
    expected = val * Decimal("0.075")
    assert calcular_inss(val) == expected

    # 3. Second bracket (1412.00 < x <= 2666.68) -> 9% on excess
    # Test value: 2000.00
    # Tier 1: 1412.00 * 0.075 = 105.90
    # Tier 2: (2000 - 1412) = 588.00 * 0.09 = 52.92
    # Total = 158.82
    val = Decimal("2000.00")
    assert abs(calcular_inss(val) - Decimal("158.82")) < Decimal("0.01")

def test_calcular_irrf() -> None:
    # Based on 2024 table in code

    # 1. Exempt (<= 2259.20)
    assert calcular_irrf(Decimal("2200.00")) == Decimal("0.00")

    # 2. First bracket (2259.21 to 2826.65) -> 7.5% - 169.44
    # Test value: 2500.00
    # 2500 * 0.075 = 187.5
    # 187.5 - 169.44 = 18.06
    val = Decimal("2500.00")
    assert abs(calcular_irrf(val) - Decimal("18.06")) < Decimal("0.01")

def test_parcelamento_esta_ativo() -> None:
    p = Parcelamento("Test", Decimal("100"), "2024-01", "2024-05")

    # Before
    assert not p.esta_ativo(datetime.date(2023, 12, 31))

    # Start (Boundary)
    assert p.esta_ativo(datetime.date(2024, 1, 1))

    # Middle
    assert p.esta_ativo(datetime.date(2024, 3, 15))

    # End (Boundary)
    assert p.esta_ativo(datetime.date(2024, 5, 31))

    # After
    assert not p.esta_ativo(datetime.date(2024, 6, 1))

def test_calcular_holerite() -> None:
    config = Configuracao(
        salario_base=Decimal("2000.00"),
        produtividade_media=Decimal("500.00"),
        meta_investimento_percentual=Decimal("0.10"),
        estado_feriados="SP",
        valor_diario_vt=Decimal("0.00"),
        valor_diario_va=Decimal("0.00")
    )
    # Mocking simple days
    dias_uteis = 20
    dias_descanso = 10

    # DSR = (500 / 20) * 10 = 250
    # Bruto = 2000 + 500 + 250 = 2750

    # INSS calculation for 2750:
    # 1412 * 0.075 = 105.90
    # (2666.68 - 1412) = 1254.68 * 0.09 = 112.9212
    # (2750 - 2666.68) = 83.32 * 0.12 = 9.9984
    # Total INSS = 105.90 + 112.9212 + 9.9984 = 228.8196 -> ~228.82

    # Base IRRF = 2750 - 228.8196 = 2521.1804
    # IRRF on 2521.1804 (Bracket 1: 7.5% - 169.44)
    # 2521.1804 * 0.075 = 189.08853
    # 189.08853 - 169.44 = 19.64853 -> ~19.65

    # Liquido = 2750 - 228.82 - 19.65 = 2501.53

    res = calcular_holerite(config, dias_uteis, dias_descanso)

    assert res["bruto"] == Decimal("2750.00")
    assert abs(res["dsr"] - Decimal("250.00")) < Decimal("0.01")
    assert abs(res["inss"] - Decimal("228.82")) < Decimal("0.01")
    assert abs(res["irrf"] - Decimal("19.65")) < Decimal("0.02") # slightly wider tolerance due to intermediate rounding
    assert abs(res["liquido"] - Decimal("2501.53")) < Decimal("0.05")

def test_load_data() -> None:
    mock_json = json.dumps({
        "configuracao": {
            "salario_base": 2772.00,
            "produtividade_media": 542.40,
            "meta_investimento_percentual": 0.20,
            "estado_feriados": "SP",
            "valor_diario_vt": 10.00,
            "valor_diario_va": 20.00
        },
        "gastos_fixos": [
            {"nome": "Aluguel", "valor": 1200.00, "categoria": "Moradia"}
        ],
        "parcelamentos": [
            {
                "nome": "Item",
                "valor_parcela": 100.00,
                "inicio": "2024-01",
                "fim": "2024-12"
            }
        ]
    })

    with patch("builtins.open", mock_open(read_data=mock_json)):
        data = load_data("dummy.json")
        assert data.configuracao.salario_base == Decimal("2772.00")
        assert data.configuracao.valor_diario_vt == Decimal("10.00")
        assert len(data.gastos_fixos) == 1
        assert data.gastos_fixos[0].nome == "Aluguel"
        assert len(data.parcelamentos) == 1

def test_gerar_projecao() -> None:
    # Setup data
    config = Configuracao(
        salario_base=Decimal("1000.00"),
        produtividade_media=Decimal("0.00"),
        meta_investimento_percentual=Decimal("0.0"),
        estado_feriados="SP",
        valor_diario_vt=Decimal("0.00"),
        valor_diario_va=Decimal("0.00")
    )
    gastos = [GastoFixo("Fix", Decimal("100.00"), "Cat")]
    # Parcelamento valid for a long time
    parc = [Parcelamento("P", Decimal("50.00"), "2000-01", "2099-12")]

    data = OrcamentoData(config, gastos, parc)

    # Generate for 1 month
    proj = gerar_projecao(data, meses=1)
    assert len(proj) == 1
    m = proj[0]

    # Verify basic flow
    # Bruto 1000 -> INSS 75.00 -> Liquido 925.00
    # Total gastos = 100 + 50 = 150
    # Saldo = 925 - 150 = 775

    assert m.salario_bruto == Decimal("1000.00")
    assert m.gastos_totais == Decimal("150.00")
    assert m.saldo_livre == m.salario_liquido - m.gastos_totais

def test_gerar_projecao_com_beneficios() -> None:
    # Setup data with benefits
    config = Configuracao(
        salario_base=Decimal("1000.00"),
        produtividade_media=Decimal("0.00"),
        meta_investimento_percentual=Decimal("0.0"),
        estado_feriados="SP",
        valor_diario_vt=Decimal("10.00"),
        valor_diario_va=Decimal("20.00")
    )
    gastos: list[GastoFixo] = []
    parc: list[Parcelamento] = []

    data = OrcamentoData(config, gastos, parc)

    proj = gerar_projecao(data, meses=1)
    m = proj[0]

    # Check calendar calculation for the current month
    uteis, descanso, uteis_beneficios = analisar_calendario(m.data.year, m.data.month, "SP")

    expected_benefits = (Decimal("10.00") + Decimal("20.00")) * uteis_beneficios

    # Holerite calculation (base 1000)
    # Bruto = 1000.
    # INSS on 1000 = 75.00
    # Liq Holerite = 925.00

    expected_liquid = Decimal("925.00") + expected_benefits

    assert m.salario_liquido == expected_liquid
