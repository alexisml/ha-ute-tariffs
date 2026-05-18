# UTE Tarifas — Documentation Index

Welcome to the UTE Tarifas documentation.  Use the table below to jump to the
section that fits your needs.

| # | Document | Who it is for |
|---|----------|---------------|
| 1 | **[User Manual (this file)](01-user-manual.md)** | Everyone |
| 2 | **[Installation & Setup](02-installation-and-setup.md)** | New users |
| 3 | **[How It Works](03-how-it-works.md)** | Curious users, advanced automations |
| 4 | **[Development Guide](04-development-guide.md)** | Contributors, price/schedule maintainers |
| 5 | **[Troubleshooting & Debugging](05-troubleshooting-and-debugging.md)** | Something is wrong |

---

## Quick-start

1. Install via HACS → **[Installation & Setup →](02-installation-and-setup.md)**
2. Add the integration from *Settings › Devices & Services › Add Integration*,
   search **UTE Tarifas**, and pick your contract type.
3. The following sensors appear under a single **UTE Tarifas** device:

   **Main sensors:**

   | Sensor | What it shows |
   |--------|---------------|
   | `sensor.ute_tarifas_current_cost` | Current UYU/kWh rate **including IVA (22 %)** |
   | `sensor.ute_tarifas_current_period` | Current period (`valle` / `llano` / `punta` / `simple`) |
   | `sensor.ute_tarifas_next_change` | Datetime of the next rate change |
   | `sensor.ute_tarifas_next_period` | Period that will be active after the next change |
   | `sensor.ute_tarifas_contract_type` | Configured contract type |

   **Diagnostic sensors** (visible in the *Diagnostics* section of the device page):

   | Sensor | What it shows |
   |--------|---------------|
   | `sensor.ute_tarifas_current_cost_excl_iva` | Current UYU/kWh rate **excluding IVA** |
   | `sensor.ute_tarifas_iva_rate` | IVA rate applied (22 %) |
   | `sensor.ute_tarifas_price_simple_low` | Simple — low tier rate excl. IVA (0–100 kWh/month) |
   | `sensor.ute_tarifas_price_simple_mid` | Simple — mid tier rate excl. IVA (101–600 kWh/month) |
   | `sensor.ute_tarifas_price_simple_high` | Simple — high tier rate excl. IVA (601+ kWh/month) |
   | `sensor.ute_tarifas_price_double_llano` | Double — llano rate excl. IVA |
   | `sensor.ute_tarifas_price_double_punta` | Double — punta rate excl. IVA |
   | `sensor.ute_tarifas_price_triple_valle` | Triple — valle rate excl. IVA |
   | `sensor.ute_tarifas_price_triple_llano` | Triple — llano rate excl. IVA |
   | `sensor.ute_tarifas_price_triple_punta` | Triple — punta rate excl. IVA |

4. Build automations that react to tariff changes — see
   **[Automation examples →](02-installation-and-setup.md#automation-examples)**

---

## Key concepts

- **Prices and schedules live in `prices.py`** — they update automatically when
  the repository is updated; no user action is required.
- **All time comparisons use UY timezone** (`America/Montevideo`) regardless of
  the timezone configured on your Home Assistant server.
- **Weekends and holidays are always all-llano** for Double contracts and
  **all-valle** for Triple contracts (standard UTE residential rule).
- **IVA (22 %)** is applied automatically.  `current_cost` always shows the
  IVA-inclusive price — the figure you see on your electricity bill.
- **Custom schedule overrides** can be set per day-type via *Settings › Devices
  & Services › UTE Tarifas › Configure*.

---

*Back to [README](../../README.md)*
