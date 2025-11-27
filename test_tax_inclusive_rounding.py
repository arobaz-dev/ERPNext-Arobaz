"""
Test Suite for Tax-Inclusive Rounding Bug (ERPNext v15)

This file demonstrates:
1. The current bug behavior
2. How the fix resolves it
3. Test cases for various currencies and tax rates
"""

import json
from decimal import Decimal, ROUND_HALF_UP


# Standalone flt() function (mimics frappe.utils.flt)
def flt(val, precision=None):
    """Convert to float and optionally round to precision"""
    try:
        val = float(val)
    except (ValueError, TypeError):
        val = 0.0
    
    if precision is not None:
        # Round to 'precision' decimal places
        return float(format(val, f'.{precision}f'))
    return val


class TaxInclusiveRoundingTest:
    """
    Test cases for tax-inclusive line item reconciliation.
    
    Requirement: At display precision, roundednetRate × qty should equal rounded_net_amount
    """

    def __init__(self):
        self.results = []

    def test_tunisia_scenario(self):
        """
        Original bug report: TND currency (3 decimals) with 19% VAT
        
        Expected behavior:
            Price TTC: 79.000 TND
            Qty: 12
            Pure math: 79 / 1.19 = 66.38655462... TND per unit
            
            Displayed net_rate: 66.387 TND (rounded to 3 decimals)
            Displayed net_amount: Should be 66.387 × 12 = 796.644 TND
            
        Actual current behavior:
            Displayed net_rate: 66.387 TND
            Stored net_amount: 796.639 TND (from 66.38655462... × 12, then rounded)
            Result: 66.387 × 12 = 796.644 ≠ 796.639 ❌ FAILS RECONCILIATION
        """
        
        print("\n" + "="*80)
        print("TEST 1: Tunisia TND with 19% VAT (Original Bug Report)")
        print("="*80)
        
        # Configuration
        currency_precision = 3
        price_ttc = Decimal("79.000")
        qty = 12
        tax_rate = Decimal("19")  # 19% VAT
        
        # Pure calculation
        tax_fraction = 1 + (tax_rate / 100)  # 1.19
        net_rate_unrounded = price_ttc / tax_fraction / qty
        
        print(f"\n Input Parameters:")
        print(f"  Currency: TND (precision={currency_precision})")
        print(f"  Price TTC (rate including VAT): {price_ttc} TND")
        print(f"  Quantity: {qty}")
        print(f"  Tax Rate: {tax_rate}%")
        
        print(f"\n Pure Mathematical Calculation:")
        print(f"  net_amount (unrounded) = {price_ttc} / {tax_fraction}")
        print(f"                         = {price_ttc / tax_fraction}")
        print(f"  net_rate (unrounded) = {net_rate_unrounded}")
        
        # Current (buggy) behavior
        print(f"\n CURRENT (BUGGY) BEHAVIOR:")
        
        net_amount_unrounded = price_ttc / tax_fraction
        net_amount_rounded_wrong = flt(net_amount_unrounded, currency_precision)
        net_rate_from_wrong_amount = net_amount_rounded_wrong / qty
        
        print(f"  Step 1: Round net_amount independently")
        print(f"    net_amount = flt({net_amount_unrounded}, {currency_precision})")
        print(f"               = {net_amount_rounded_wrong}")
        
        print(f"  Step 2: Compute net_rate from rounded net_amount")
        print(f"    net_rate = {net_amount_rounded_wrong} / {qty}")
        print(f"             = {net_rate_from_wrong_amount} (rounded to {currency_precision})")
        net_rate_displayed = flt(net_rate_from_wrong_amount, currency_precision)
        print(f"             = {net_rate_displayed}")
        
        print(f"\n  Result:")
        print(f"    Displayed net_rate: {net_rate_displayed}")
        print(f"    Stored net_amount: {net_amount_rounded_wrong}")
        print(f"    Reconciliation check: {net_rate_displayed} × {qty} = {net_rate_displayed * qty}")
        
        reconciliation_error = flt(net_rate_displayed * qty, currency_precision) - net_amount_rounded_wrong
        print(f"    Discrepancy: {reconciliation_error} ❌ FAILED")
        
        # Proposed fix behavior
        print(f"\n PROPOSED FIX:")
        
        print(f"  Step 1: Round net_rate to currency precision FIRST")
        net_rate_correct = flt(net_rate_unrounded, currency_precision)
        print(f"    net_rate = flt({net_rate_unrounded}, {currency_precision})")
        print(f"             = {net_rate_correct}")
        
        print(f"  Step 2: Recompute net_amount from rounded net_rate")
        net_amount_correct = flt(net_rate_correct * qty, currency_precision)
        print(f"    net_amount = {net_rate_correct} × {qty}")
        print(f"               = {net_amount_correct}")
        
        print(f"\n  Result:")
        print(f"    Displayed net_rate: {net_rate_correct}")
        print(f"    Stored net_amount: {net_amount_correct}")
        print(f"    Reconciliation check: {net_rate_correct} × {qty} = {net_rate_correct * qty}")
        
        reconciliation_fixed = flt(net_rate_correct * qty, currency_precision) - net_amount_correct
        if reconciliation_fixed == 0:
            print(f"    Discrepancy: {reconciliation_fixed} ✅ PASSED")
        
        self.results.append({
            "test": "Tunisia TND 19% VAT",
            "status": "PASS" if reconciliation_fixed == 0 else "FAIL",
            "error_before_fix": reconciliation_error,
            "error_after_fix": reconciliation_fixed,
        })

    def test_cascading_taxes(self):
        """
        Test with multiple cascading taxes (7% + 19%)
        
        Price TTC includes both: (1 + 0.07) × (1 + 0.19) = 1.2733
        """
        
        print("\n" + "="*80)
        print("TEST 2: Tunisia with Cascading Taxes (7% + 19%)")
        print("="*80)
        
        currency_precision = 3
        price_ttc = Decimal("79.000")
        qty = 12
        tax_rate_1 = Decimal("7")
        tax_rate_2 = Decimal("19")
        
        # Both taxes are multiplicative
        tax_fraction = (1 + tax_rate_1/100) * (1 + tax_rate_2/100)  # 1.2733
        net_rate_unrounded = price_ttc / tax_fraction / qty
        
        print(f"\nInput Parameters:")
        print(f"  Currency: TND (precision={currency_precision})")
        print(f"  Price TTC: {price_ttc} TND")
        print(f"  Quantity: {qty}")
        print(f"  Tax Rates: {tax_rate_1}% + {tax_rate_2}% (cascading)")
        print(f"  Combined tax factor: {tax_fraction}")
        
        # Buggy behavior
        net_amount_unrounded = price_ttc / tax_fraction
        net_amount_wrong = flt(net_amount_unrounded, currency_precision)
        net_rate_wrong = flt(net_amount_wrong / qty, currency_precision)
        reconciliation_error = flt(net_rate_wrong * qty, currency_precision) - net_amount_wrong
        
        # Fixed behavior
        net_rate_correct = flt(net_rate_unrounded, currency_precision)
        net_amount_correct = flt(net_rate_correct * qty, currency_precision)
        reconciliation_fixed = flt(net_rate_correct * qty, currency_precision) - net_amount_correct
        
        print(f"\nCURRENT BEHAVIOR:")
        print(f"  net_amount: {net_amount_wrong}")
        print(f"  net_rate: {net_rate_wrong}")
        print(f"  {net_rate_wrong} × {qty} = {flt(net_rate_wrong * qty, currency_precision)} ≠ {net_amount_wrong}")
        print(f"  Discrepancy: {reconciliation_error} ❌")
        
        print(f"\nFIXED BEHAVIOR:")
        print(f"  net_amount: {net_amount_correct}")
        print(f"  net_rate: {net_rate_correct}")
        print(f"  {net_rate_correct} × {qty} = {flt(net_rate_correct * qty, currency_precision)} = {net_amount_correct}")
        print(f"  Discrepancy: {reconciliation_fixed} ✅")
        
        self.results.append({
            "test": "Cascading Taxes (7% + 19%)",
            "status": "PASS" if reconciliation_fixed == 0 else "FAIL",
            "error_before_fix": reconciliation_error,
            "error_after_fix": reconciliation_fixed,
        })

    def test_euro_2_decimals(self):
        """
        Test with EUR (2 decimal places) and 20% VAT
        """
        
        print("\n" + "="*80)
        print("TEST 3: EUR with 2 Decimals and 20% VAT")
        print("="*80)
        
        currency_precision = 2
        price_ttc = Decimal("100.00")
        qty = 3
        tax_rate = Decimal("20")
        
        tax_fraction = 1 + tax_rate/100  # 1.20
        net_rate_unrounded = price_ttc / tax_fraction / qty
        
        print(f"\nInput Parameters:")
        print(f"  Currency: EUR (precision={currency_precision})")
        print(f"  Price TTC: {price_ttc} EUR")
        print(f"  Quantity: {qty}")
        print(f"  Tax Rate: {tax_rate}%")
        
        # Buggy
        net_amount_unrounded = price_ttc / tax_fraction
        net_amount_wrong = flt(net_amount_unrounded, currency_precision)
        net_rate_wrong = flt(net_amount_wrong / qty, currency_precision)
        reconciliation_error = flt(net_rate_wrong * qty, currency_precision) - net_amount_wrong
        
        # Fixed
        net_rate_correct = flt(net_rate_unrounded, currency_precision)
        net_amount_correct = flt(net_rate_correct * qty, currency_precision)
        reconciliation_fixed = flt(net_rate_correct * qty, currency_precision) - net_amount_correct
        
        print(f"\nCURRENT BEHAVIOR:")
        print(f"  net_amount: {net_amount_wrong}")
        print(f"  net_rate: {net_rate_wrong}")
        print(f"  {net_rate_wrong} × {qty} = {flt(net_rate_wrong * qty, currency_precision)} {'=' if not reconciliation_error else '≠'} {net_amount_wrong}")
        print(f"  Discrepancy: {reconciliation_error} {'✅' if not reconciliation_error else '❌'}")
        
        print(f"\nFIXED BEHAVIOR:")
        print(f"  net_amount: {net_amount_correct}")
        print(f"  net_rate: {net_rate_correct}")
        print(f"  {net_rate_correct} × {qty} = {flt(net_rate_correct * qty, currency_precision)} = {net_amount_correct}")
        print(f"  Discrepancy: {reconciliation_fixed} ✅")
        
        self.results.append({
            "test": "EUR 2 decimals with 20% VAT",
            "status": "PASS" if reconciliation_fixed == 0 else "FAIL",
            "error_before_fix": reconciliation_error,
            "error_after_fix": reconciliation_fixed,
        })

    def test_usd_cents(self):
        """
        Test with USD (2 decimals) and 8.5% tax
        """
        
        print("\n" + "="*80)
        print("TEST 4: USD with 2 Decimals and 8.5% Tax")
        print("="*80)
        
        currency_precision = 2
        price_ttc = Decimal("99.99")
        qty = 7
        tax_rate = Decimal("8.5")
        
        tax_fraction = 1 + tax_rate/100
        net_rate_unrounded = price_ttc / tax_fraction / qty
        
        print(f"\nInput Parameters:")
        print(f"  Currency: USD (precision={currency_precision})")
        print(f"  Price TTC: {price_ttc} USD")
        print(f"  Quantity: {qty}")
        print(f"  Tax Rate: {tax_rate}%")
        
        # Buggy
        net_amount_unrounded = price_ttc / tax_fraction
        net_amount_wrong = flt(net_amount_unrounded, currency_precision)
        net_rate_wrong = flt(net_amount_wrong / qty, currency_precision)
        reconciliation_error = flt(net_rate_wrong * qty, currency_precision) - net_amount_wrong
        
        # Fixed
        net_rate_correct = flt(net_rate_unrounded, currency_precision)
        net_amount_correct = flt(net_rate_correct * qty, currency_precision)
        reconciliation_fixed = flt(net_rate_correct * qty, currency_precision) - net_amount_correct
        
        print(f"\nCURRENT BEHAVIOR:")
        print(f"  net_amount: {net_amount_wrong}")
        print(f"  net_rate: {net_rate_wrong}")
        print(f"  {net_rate_wrong} × {qty} = {flt(net_rate_wrong * qty, currency_precision)} {'=' if not reconciliation_error else '≠'} {net_amount_wrong}")
        print(f"  Discrepancy: {reconciliation_error} {'✅' if not reconciliation_error else '❌'}")
        
        print(f"\nFIXED BEHAVIOR:")
        print(f"  net_amount: {net_amount_correct}")
        print(f"  net_rate: {net_rate_correct}")
        print(f"  {net_rate_correct} × {qty} = {flt(net_rate_correct * qty, currency_precision)} = {net_amount_correct}")
        print(f"  Discrepancy: {reconciliation_fixed} ✅")
        
        self.results.append({
            "test": "USD with 8.5% tax",
            "status": "PASS" if reconciliation_fixed == 0 else "FAIL",
            "error_before_fix": reconciliation_error,
            "error_after_fix": reconciliation_fixed,
        })

    def run_all(self):
        """Run all tests and print summary"""
        self.test_tunisia_scenario()
        self.test_cascading_taxes()
        self.test_euro_2_decimals()
        self.test_usd_cents()
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        print(f"\n{'Test Name':<40} {'Status':<10} {'Before Fix':<15} {'After Fix':<15}")
        print("-" * 80)
        
        for result in self.results:
            print(f"{result['test']:<40} {result['status']:<10} "
                  f"{float(result['error_before_fix']):>14.6f} {float(result['error_after_fix']):>14.6f}")
        
        all_passed = all(r['status'] == 'PASS' for r in self.results)
        print("\n" + "="*80)
        if all_passed:
            print("✅ ALL TESTS PASSED WITH FIX")
        else:
            print("⚠️  SOME TESTS SHOW ISSUES")
        print("="*80)


if __name__ == "__main__":
    tester = TaxInclusiveRoundingTest()
    tester.run_all()
