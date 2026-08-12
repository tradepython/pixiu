current_time = Time()

if market_event_case == "field_visibility":
    if current_time == visible_before_time:
        upcoming = GetUpcomingMarketEvents(currency="USD", within_seconds=600, min_impact="high")
        assertEqual(1, len(upcoming))
        payload = upcoming[0]["payload"]
        assertEqual("180K", payload.get("forecast"))
        assertIsNone(payload.get("actual"))
        assertEqual("Nonfarm Payrolls", upcoming[0]["title"])
    elif current_time == release_time:
        latest = GetLatestMarketEvents(currency="USD", lookback_seconds=600, min_impact="high")
        assertEqual(1, len(latest))
        assertEqual("220K", latest[0]["payload"].get("actual"))
        set_test_result("OK")

elif market_event_case == "instrument_filter":
    if current_time == instrument_event_time:
        by_instrument = GetMarketEvents(instrument_id="stock:NASDAQ:AAPL", asset_class="stock")
        assertEqual(1, len(by_instrument))
        assertEqual("earnings", by_instrument[0]["type"])
        assertEqual("issuer:apple", by_instrument[0]["issuer_ids"][0])

        by_symbol_venue = GetMarketEvents(symbol="AAPL", venue="NASDAQ", asset_class="stock")
        assertEqual(1, len(by_symbol_venue))

        wrong_venue = GetMarketEvents(symbol="AAPL", venue="NYSE", asset_class="stock")
        assertEqual(0, len(wrong_venue))
        set_test_result("OK")
