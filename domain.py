import calendar
import json
import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple, Dict

import holidays

@dataclass
class Configuracao:
    salario_base: Decimal
    produtividade_media: Decimal
    meta_investimento_percentual: Decimal
    estado_feriados: str
    valor_diario_vt: Decimal
    valor_diario_va: Decimal

@dataclass
class GastoFixo:
    nome: str
    valor: Decimal
    categoria: str

@dataclass
class Parcelamento:
    nome: str
    valor_parcela: Decimal
    inicio: str  # YYYY-MM
    fim: str     # YYYY-MM

    def esta_ativo(self, mes_referencia: datetime.date) -> bool:
        start_date = datetime.datetime.strptime(self.inicio, "%Y-%m").date()
        # Ensure start_date is the first of the month
        start_date = start_date.replace(day=1)

        end_date = datetime.datetime.strptime(self.fim, "%Y-%m").date()
        # Ensure end_date includes the entire month (set to last day of that month for comparison,
        # or just compare year/month)
        # Easier: check if start_date <= mes_referencia <= end_date (comparing first of months)
        end_date = end_date.replace(day=1)

        ref = mes_referencia.replace(day=1)
        return start_date <= ref <= end_date

@dataclass
class OrcamentoData:
    configuracao: Configuracao
    gastos_fixos: List[GastoFixo]
    parcelamentos: List[Parcelamento]

@dataclass
class MesProjecao:
    data: datetime.date
    salario_bruto: Decimal
    desconto_inss: Decimal
    desconto_irrf: Decimal
    salario_liquido: Decimal
    gastos_totais: Decimal
    gastos_fixos: Decimal
    gastos_parcelados: Decimal
    saldo_livre: Decimal
    meta_investimento: Decimal
    dias_uteis: int
    dias_descanso: int
    dsr_valor: Decimal
    detalhes_parcelas: List[str]

def load_data(filepath: str = "orcamento.json") -> OrcamentoData:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = Configuracao(
        salario_base=Decimal(str(data["configuracao"]["salario_base"])),
        produtividade_media=Decimal(str(data["configuracao"]["produtividade_media"])),
        meta_investimento_percentual=Decimal(str(data["configuracao"]["meta_investimento_percentual"])),
        estado_feriados=data["configuracao"]["estado_feriados"],
        valor_diario_vt=Decimal(str(data["configuracao"].get("valor_diario_vt", "0.00"))),
        valor_diario_va=Decimal(str(data["configuracao"].get("valor_diario_va", "0.00")))
    )

    gastos_fixos = [
        GastoFixo(
            nome=g["nome"],
            valor=Decimal(str(g["valor"])),
            categoria=g["categoria"]
        ) for g in data["gastos_fixos"]
    ]

    parcelamentos = [
        Parcelamento(
            nome=p["nome"],
            valor_parcela=Decimal(str(p["valor_parcela"])),
            inicio=p["inicio"],
            fim=p["fim"]
        ) for p in data["parcelamentos"]
    ]

    return OrcamentoData(config, gastos_fixos, parcelamentos)

def analisar_calendario(ano: int, mes: int, estado: str) -> Tuple[int, int, int]:
    """
    Retorna (dias_uteis, dias_descanso, dias_uteis_beneficios).
    Dias úteis: Segunda a Sábado (exceto feriados).
    Dias descanso: Domingos + Feriados.
    Dias úteis benefícios: Segunda a Sexta (exceto feriados).
    """
    br_holidays = holidays.country_holidays("BR", subdiv=estado, years=ano)
    month_days = calendar.monthrange(ano, mes)[1]

    dias_uteis = 0
    dias_descanso = 0
    dias_uteis_beneficios = 0

    for day in range(1, month_days + 1):
        date_obj = datetime.date(ano, mes, day)

        is_sunday = (date_obj.weekday() == 6)
        is_holiday = (date_obj in br_holidays)
        is_saturday = (date_obj.weekday() == 5)

        if is_sunday or is_holiday:
            dias_descanso += 1
        else:
            # Segunda (0) a Sabado (5) e nao feriado
            dias_uteis += 1
            if not is_saturday:
                dias_uteis_beneficios += 1

    return dias_uteis, dias_descanso, dias_uteis_beneficios

def calcular_inss(bruto: Decimal) -> Decimal:
    # Tabela Progressiva INSS 2024 (aproximada)
    # Faixas: 1412.00 (7.5%), 2666.68 (9%), 4000.03 (12%), Teto 7786.02 (14%)
    faixas = [
        (Decimal("1412.00"), Decimal("0.075")),
        (Decimal("2666.68"), Decimal("0.09")),
        (Decimal("4000.03"), Decimal("0.12")),
        (Decimal("7786.02"), Decimal("0.14")),
    ]

    desconto = Decimal("0.00")
    anterior = Decimal("0.00")

    for limite, aliquota in faixas:
        if bruto > anterior:
            base = min(bruto, limite) - anterior
            desconto += base * aliquota
            anterior = limite
        else:
            break

    return desconto

def calcular_irrf(base_calculo: Decimal) -> Decimal:
    # Tabela Progressiva IRRF (Vigencia 2024 - 2 salarios minimos isencao simplificada ou tabela normal)
    # Usando tabela padrao
    # Ate 2259.20: Isento
    # 2259.21 a 2826.65: 7.5% (Deducao 169.44)
    # 2826.66 a 3751.05: 15% (Deducao 381.44)
    # 3751.06 a 4664.68: 22.5% (Deducao 662.77)
    # Acima 4664.68: 27.5% (Deducao 896.00)

    if base_calculo <= Decimal("2259.20"):
        return Decimal("0.00")
    elif base_calculo <= Decimal("2826.65"):
        return (base_calculo * Decimal("0.075")) - Decimal("169.44")
    elif base_calculo <= Decimal("3751.05"):
        return (base_calculo * Decimal("0.15")) - Decimal("381.44")
    elif base_calculo <= Decimal("4664.68"):
        return (base_calculo * Decimal("0.225")) - Decimal("662.77")
    else:
        return (base_calculo * Decimal("0.275")) - Decimal("896.00")

def calcular_holerite(config: Configuracao, dias_uteis: int, dias_descanso: int) -> Dict[str, Decimal]:
    if dias_uteis == 0:
        dsr = Decimal("0.00")
    else:
        dsr = (config.produtividade_media / Decimal(dias_uteis)) * Decimal(dias_descanso)

    bruto = config.salario_base + config.produtividade_media + dsr

    inss = calcular_inss(bruto)

    # Base IRRF = Bruto - INSS - Dependentes (assumindo 0 aqui)
    base_irrf = bruto - inss
    irrf = calcular_irrf(base_irrf)

    liquido = bruto - inss - irrf

    return {
        "bruto": bruto,
        "inss": inss,
        "irrf": irrf,
        "liquido": liquido,
        "dsr": dsr
    }

def gerar_projecao(dados: OrcamentoData, meses: int = 12) -> List[MesProjecao]:
    projecao = []
    data_atual = datetime.date.today().replace(day=1)

    for i in range(meses):
        # Calcular mes alvo
        mes_ano = i + data_atual.month
        ano_offset = (mes_ano - 1) // 12
        mes_real = ((mes_ano - 1) % 12) + 1
        ano_real = data_atual.year + ano_offset

        data_ref = datetime.date(ano_real, mes_real, 1)

        # 1. Calendario
        dias_uteis, dias_descanso, dias_uteis_beneficios = analisar_calendario(ano_real, mes_real, dados.configuracao.estado_feriados)

        # 2. Holerite
        holerite = calcular_holerite(dados.configuracao, dias_uteis, dias_descanso)

        # Calcular benefícios (VA + VT)
        total_beneficios = (dados.configuracao.valor_diario_vt + dados.configuracao.valor_diario_va) * dias_uteis_beneficios

        # Adicionar benefícios à receita líquida
        salario_liquido_com_beneficios = holerite["liquido"] + total_beneficios

        # 3. Gastos Fixos
        total_fixos = sum((g.valor for g in dados.gastos_fixos), start=Decimal("0.00"))

        # 4. Parcelamentos
        total_parcelas = Decimal("0.00")
        detalhes_parcelas = []
        for p in dados.parcelamentos:
            if p.esta_ativo(data_ref):
                total_parcelas += p.valor_parcela
                detalhes_parcelas.append(p.nome)

        gastos_totais = total_fixos + total_parcelas
        saldo_livre = salario_liquido_com_beneficios - gastos_totais
        meta_investimento = salario_liquido_com_beneficios * dados.configuracao.meta_investimento_percentual

        projecao.append(MesProjecao(
            data=data_ref,
            salario_bruto=holerite["bruto"],
            desconto_inss=holerite["inss"],
            desconto_irrf=holerite["irrf"],
            salario_liquido=salario_liquido_com_beneficios,
            gastos_totais=gastos_totais,
            gastos_fixos=total_fixos,
            gastos_parcelados=total_parcelas,
            saldo_livre=saldo_livre,
            meta_investimento=meta_investimento,
            dias_uteis=dias_uteis,
            dias_descanso=dias_descanso,
            dsr_valor=holerite["dsr"],
            detalhes_parcelas=detalhes_parcelas
        ))

    return projecao
