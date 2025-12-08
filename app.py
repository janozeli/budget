from decimal import Decimal
import locale
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Header, Footer, Static, DataTable, TabbedContent, TabPane, Label
from textual.binding import Binding

import domain

# Tentar configurar locale para pt_BR, fallback para padrao se nao disponivel
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR')
    except locale.Error:
        pass  # Mantem locale padrao do sistema

def format_currency(value: Decimal) -> str:
    # Fallback manual format se locale nao ajudar
    try:
        return locale.currency(value, grouping=True)
    except (ValueError, TypeError):
        return f"R$ {value:,.2f}"

class KPICard(Static):
    """Um widget para mostrar um valor chave."""

    def __init__(self, title: str, value: str, id: str = ""):
        super().__init__(id=id)
        self.title = title
        self.value = value

    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="kpi-title")
        yield Label(self.value, classes="kpi-value")

    def update_value(self, value: str) -> None:
        self.query_one(".kpi-value", Label).update(value)

class TuiFinanceira(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    KPICard {
        width: 1fr;
        height: 10;
        background: $surface;
        border: solid $primary;
        margin: 1;
        content-align: center middle;
    }

    .kpi-title {
        text-opacity: 0.6;
        text-style: bold;
    }

    .kpi-value {
        text-style: bold;
        font-size: 2;
        padding-top: 1;
    }

    #dashboard-grid {
        height: auto;
        margin-bottom: 2;
    }

    DataTable {
        height: 1fr;
    }

    .parcela-end {
        color: $success;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Sair"),
        Binding("r", "reload_data", "Recarregar"),
    ]

    data: domain.OrcamentoData
    projecao: list[domain.MesProjecao]

    def on_mount(self) -> None:
        self.action_reload_data()

    def action_reload_data(self) -> None:
        try:
            self.data = domain.load_data()
            self.projecao = domain.gerar_projecao(self.data)
            self.update_dashboard()
            self.notify("Dados recarregados com sucesso!")
        except Exception as e:
            self.notify(f"Erro ao carregar dados: {e}", severity="error")

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent():
            with TabPane("Visão Mês Atual", id="tab-dashboard"):
                yield VerticalScroll(
                    Horizontal(
                        KPICard("Receita Líquida", "R$ 0,00", id="kpi-receita"),
                        KPICard("Gastos Totais", "R$ 0,00", id="kpi-gastos"),
                        id="dashboard-grid"
                    ),
                    Horizontal(
                        KPICard("Meta Aporte", "R$ 0,00", id="kpi-meta"),
                        KPICard("Saldo Livre", "R$ 0,00", id="kpi-saldo"),
                        id="dashboard-grid-2"
                    )
                )

            with TabPane("Projeção 12 Meses", id="tab-projecao"):
                yield DataTable()

        yield Footer()

    def update_dashboard(self) -> None:
        if not self.projecao:
            return

        # 1. Update KPIs (Mes Atual - indice 0)
        atual = self.projecao[0]

        self.query_one("#kpi-receita", KPICard).update_value(format_currency(atual.salario_liquido))
        self.query_one("#kpi-gastos", KPICard).update_value(format_currency(atual.gastos_totais))
        self.query_one("#kpi-meta", KPICard).update_value(format_currency(atual.meta_investimento))
        self.query_one("#kpi-saldo", KPICard).update_value(format_currency(atual.saldo_livre))

        # 2. Update Table
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns(
            "Mês",
            "Dias Úteis",
            "DSR",
            "Receita Líq.",
            "Gastos Totais",
            "Saldo Livre",
            "Parcelas Ativas"
        )

        # Track previous installments to highlight changes
        for i, mes in enumerate(self.projecao):
            mes_str = mes.data.strftime("%b/%Y")
            curr_parcelas_count = len(mes.detalhes_parcelas)

            # Formatar lista de parcelas
            parcelas_str = ", ".join(mes.detalhes_parcelas) if mes.detalhes_parcelas else "-"

            # Simple highlight logic: if parcelas count dropped, maybe highlight the row or cell?
            # Textual DataTable supports styling rows/cells?
            # We can use rich text or just logic.

            # Let's verify if a installment ended compared to previous month
            # (In this logic, we iterate forward. If previous month had more installments,
            # this month represents a "relief".)

            # Note: The logic in prompt says "Visual highlight when an installment ends (saldo livre increases)".
            # A simple way is to check if saldo livre jumped significantly or parcel count dropped.

            styled_saldo = format_currency(mes.saldo_livre)
            if i > 0:
                prev_mes = self.projecao[i-1]
                if curr_parcelas_count < len(prev_mes.detalhes_parcelas):
                     # Highlight saldo because an installment ended
                     styled_saldo = f"[bold green]{styled_saldo}[/]"

            table.add_row(
                mes_str,
                str(mes.dias_uteis),
                format_currency(mes.dsr_valor),
                format_currency(mes.salario_liquido),
                format_currency(mes.gastos_totais),
                styled_saldo,
                parcelas_str
            )

if __name__ == "__main__":
    app = TuiFinanceira()
    app.run()
