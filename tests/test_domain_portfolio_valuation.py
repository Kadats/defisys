from backend.src.domain.portfolio import calculate_portfolio_value


def test_calculate_portfolio_value_includes_all_components():
    active_lps = [
        {"fees_accrued_usdt": 5.0, "fees_accrued_btc": 0.001},
    ]
    active_shorts = [
        {"collateral_usd": 200.0, "entry_price": 50000.0, "btc_amount": 0.002},
    ]

    def _lp_value(_lp, _price):
        return 300.0, 0.0, 0.0

    current_price = 52000.0
    value = calculate_portfolio_value(
        btc_hodl_balance=0.01,
        btc_collateral_balance=0.02,
        current_btc_price=current_price,
        usd_balance=1000.0,
        active_lps=active_lps,
        active_shorts=active_shorts,
        yield_total_balance=50.0,
        total_debt_usd=100.0,
        get_lp_value_fn=_lp_value,
    )

    expected_lp = 300.0 + 5.0 + (0.001 * current_price)
    expected_short = 200.0 + ((50000.0 - current_price) * 0.002)
    expected = ((0.01 + 0.02) * current_price) + 1000.0 + expected_lp + expected_short + 50.0 - 100.0
    assert value == expected
