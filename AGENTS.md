# AGENTS.md

This document serves as the authoritative guide for AI agents and developers working on the `tui-financeira` project.

## 1. Project Overview
**tui-financeira** is a Terminal User Interface (TUI) application built with Python and [Textual](https://textual.textualize.io/). It calculates and projects personal budget scenarios, taking into account Brazilian payroll specificities such as Dynamic Holidays, Weekly Rest (DSR), INSS, and IRRF taxes.

## 2. Technology Stack & Environment
*   **Language:** Python 3.14+
*   **Dependency Manager:** `uv`
*   **UI Framework:** `textual`
*   **Domain Libraries:** `holidays` (for Brazilian holidays)
*   **Linting/Formatting:** `ruff`
*   **Static Analysis:** `mypy` (strict mode)

### Environment Setup
The project uses `uv` for dependency management.
```bash
# Install dependencies
uv sync
```

## 3. Code Organization
*   **`app.py`**: Main entry point. Contains the UI logic, widgets (`KPICard`, `DataTable`), and event handling (`action_reload_data`).
*   **`domain.py`**: Contains the core business logic and data structures (`dataclass`). Handles tax calculations, holiday logic, and projections.
*   **`orcamento.json`**: Stores persistent user data (configuration, fixed expenses, installments).
*   **`pyproject.toml`**: Configuration for build, dependencies, and tools (`ruff`, `mypy`).

## 4. Coding Standards & Verification
**All changes must pass strict verification before submission.**

### Linting & Formatting
We use `ruff` for both linting and formatting.
```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking
We use `mypy` in **strict mode**. All code must be fully typed.
```bash
uv run mypy .
```

### Testing
*Currently, there are no explicit unit tests.*
*   **Future Requirement:** When adding tests, place them in a `tests/` directory and use `pytest`.
*   **Manual Verification:** Run the application to verify UI changes.

## 5. Business Logic Details
The `domain.py` file encapsulates the financial logic.

### 5.1. Calendar & Workdays
*   **Workdays (Dias Úteis):** Monday through Saturday, excluding holidays.
*   **Rest Days (Dias Descanso):** Sundays and National/State Holidays.
*   **Library:** Uses `holidays` library dynamically based on the state configured in `orcamento.json` (e.g., "SP").

### 5.2. Payroll Calculations
*   **DSR (Descanso Semanal Remunerado):**
    `DSR = (Produtividade / Dias Úteis) * Dias Descanso`
*   **Gross Salary (Salário Bruto):**
    `Base Salary + Productivity + DSR`
*   **INSS:** Calculated using the 2024 progressive table (ranges: 7.5%, 9%, 12%, 14%).
*   **IRRF:** Calculated using the 2024 progressive table (ranges: 7.5%, 15%, 22.5%, 27.5%) on the base `(Gross - INSS)`.

### 5.3. Projections
*   The system projects 12 months into the future starting from the current month.
*   **Installments (Parcelamentos):** Checked against the projection month (`start <= month <= end`).
*   **Free Balance (Saldo Livre):** `Net Salary - (Fixed Expenses + Active Installments)`.

## 6. Data Structure (`orcamento.json`)
Modify this file to test different scenarios.
```json
{
  "configuracao": {
    "salario_base": 2772.00,
    "produtividade_media": 542.40,
    "meta_investimento_percentual": 0.20,
    "estado_feriados": "SP"
  },
  "gastos_fixos": [
    {"nome": "Aluguel", "valor": 1200.00, "categoria": "Moradia"}
  ],
  "parcelamentos": [
    {
      "nome": "Item",
      "valor_parcela": 100.00,
      "inicio": "YYYY-MM",
      "fim": "YYYY-MM"
    }
  ]
}
```

## 7. Running the Application
To launch the TUI:
```bash
uv run app.py
```
*   **Keys:**
    *   `q`: Quit
    *   `r`: Reload data from `orcamento.json` (useful for hot-reloading data tweaks)

## 8. Development Guidelines
1.  **Read-only Verification:** Always verify file contents after modification.
2.  **Edit Source:** Do not edit generated files (though none exist currently).
3.  **Strict Types:** Ensure no `Any` types leak into the codebase unless absolutely necessary and documented.
4.  **UI Updates:** When modifying `app.py`, ensure the `ComposeResult` and update methods (`update_dashboard`) are synchronized.
