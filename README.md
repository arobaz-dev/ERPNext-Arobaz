# ERPNext-Arobaz

Clean ERPNext implementation with tax inclusive rounding fix.

## Contents

- **frappe/** - Frappe Framework
- **erpnext/** - ERPNext application with tax fix
- **sites/** - Site configuration
- **fix_tax_inclusive_rounding.patch** - Tax rounding correction
- **test_tax_inclusive_rounding.py** - Tests for tax fix

## Tax Inclusive Rounding Fix

Applied to `erpnext/controllers/taxes_and_totals.py` (lines 304-310)

The fix ensures correct rounding for tax-inclusive items:
- Round `net_rate` first
- Derive `net_amount` from rounded `net_rate × qty`
- Maintains: `rounded_net_rate × qty = rounded_net_amount`

## Quick Start

1. Clone repository
2. Apply tax patch if needed
3. Run tests: `python test_tax_inclusive_rounding.py`
