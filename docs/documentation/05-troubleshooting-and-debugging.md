# Troubleshooting & Debugging

## All sensors show "Unknown" or "Unavailable"

**Most likely cause:** no `PriceRange` in `prices.py` covers today's date.

Check:
1. Open `custom_components/ute_tarifas/prices.py`.
2. Verify that at least one `PriceRange` has `start ≤ today ≤ end`.
3. Verify the same for `UTE_SCHEDULE_RANGES[your_contract_type]`.

Enable debug logging (see below) — a `"Tariff calculation failed"` log line
with `UpdateFailed` confirms this is the cause.

---

## Integration fails to load after HA restart

Check **Settings › System › Logs** for errors from `custom_components.ute_tarifas`.

Common causes:

| Error message | Fix |
|---------------|-----|
| `No active price range for YYYY-MM-DD` | Add a `PriceRange` covering today in `prices.py`. |
| `No active schedule range for YYYY-MM-DD` | Add a `ScheduleRange` covering today in `prices.py`. |
| `ModuleNotFoundError: holidays` | HACS did not install requirements. Restart HA; if it persists, reinstall the integration. |

---

## Wrong period is shown

1. Confirm the **Current Period** sensor matches the expected UTE schedule for
   your contract type and the current UY local time.
2. Check that your HA server clock is correct — the integration converts to
   `America/Montevideo` internally, but relies on `dt_util.now()` which uses
   the system clock.
3. If you have set a **custom punta window** (e.g. `17-21` instead of the
   default `18-22`), confirm it matches your UTE plan.  You can reset it to
   the default in **Configure**.

---

## Holidays are not being detected

1. Confirm **Apply national holidays** is enabled. You can toggle this in the
   integration options: **Settings › Devices & Services › UTE Tarifas › Configure**.
2. The country is fixed to `UY` (Uruguay) — the `holidays` package is queried
   for Uruguayan national holidays.
3. The `holidays` package must recognise the date as a holiday.  You can test
   in Python:
   ```python
   import holidays
   from datetime import date
   d = date(2026, 1, 1)           # New Year's Day
   print(d in holidays.country_holidays("UY", years=d.year))  # True
   ```
4. If the package does not list the date, it may not be a *national* holiday in
   the `holidays` database.  You can work around this by disabling holiday
   detection and treating the day as a weekday.

---

## `next_change` sensor shows a date far in the future

This is expected when today falls in the last period of the day and the next
event is `prices.py` boundary (e.g. a future price update).  The sensor always
reports the **earlier** of the next block boundary and the next
pricing/schedule update.

If the value looks wrong, enable debug logging and look for
`"next_tariff_data_change"` in the logs.

---

## Enabling debug logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.ute_tarifas: debug
```

Restart Home Assistant.  The integration will log:

- `"Tariff calculation failed: …"` — price/schedule range not found.
- Coordinator poll cycle messages — shows when sensors are updated.

---

## Getting help

- Open an issue at <https://github.com/alexisml/ha-ute-tariffs/issues>.
- Include your HA version, the integration version (from HACS), and any
  relevant log lines.

---

*← [Development Guide](04-development-guide.md) · [User Manual](01-user-manual.md)*
