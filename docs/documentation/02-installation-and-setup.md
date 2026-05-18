# Installation & Setup

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Home Assistant | 2024.6.0 |
| HACS | 2.0+ (for HACS install) |
| Internet access | Not required — all data is local |

---

## Installing via HACS (recommended)

1. Open HACS in your Home Assistant sidebar.
2. Click **Custom repositories** (top-right ⋮ menu).
3. Add `https://github.com/alexisml/UTE-Tarifas` as an **Integration**.
4. Search for **UTE Tarifas** and click **Download**.
5. Restart Home Assistant.

---

## Installing manually

1. Download or clone this repository.
2. Copy the `custom_components/ute_tarifas/` folder into your Home Assistant
   `config/custom_components/` directory.
3. Restart Home Assistant.

---

## Adding the integration

1. Go to **Settings › Devices & Services › + Add Integration**.
2. Search for **UTE Tarifas** and select it.
3. Fill in the setup form:

### Configuration fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| **Residential contract type** | Yes | `simple` | Your UTE plan: `simple`, `double`, or `triple`. |
| **Workday schedule override** | No | *(built-in)* | Custom time-of-use blocks for weekdays. Leave blank to use the canonical UTE schedule. |
| **Weekend schedule override** | No | *(all-valle)* | Custom blocks for Saturdays and Sundays. |
| **Holiday schedule override** | No | *(all-valle)* | Custom blocks for national holidays. |
| **Holiday country code** | No | `UY` | ISO 3166-1 alpha-2 code used to identify national holidays (e.g. `UY`, `AR`). |
| **Apply national holidays** | No | `true` | When enabled, holidays use the holiday schedule instead of the weekday schedule. |

### Schedule string format

```
HH:MM-HH:MM:period,HH:MM-HH:MM:period,...
```

Valid period names: `valle`, `llano`, `punta`, `simple`.

Use `00:00` as the **end time** to mean "until midnight" (the block wraps
around to the next calendar day).

**Example — standard Double workday schedule:**

```
00:00-07:00:valle,07:00-17:00:punta,17:00-00:00:valle
```

**Example — standard Triple workday schedule:**

```
00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano
```

Leaving a schedule field blank falls back to the built-in canonical schedule
defined in `prices.py`, which updates automatically when the repository is
updated.

---

## Updating schedule overrides later

Go to **Settings › Devices & Services › UTE Tarifas › Configure** to open the
options flow.  Clearing a field reverts that day type to the canonical UTE
default.

---

## Verifying the install

After setup, a **UTE Tarifas** device should appear under
**Settings › Devices & Services › Devices**, containing five sensors:

- `sensor.ute_tarifas_current_cost`
- `sensor.ute_tarifas_current_period`
- `sensor.ute_tarifas_next_change`
- `sensor.ute_tarifas_next_period`
- `sensor.ute_tarifas_contract_type`

All sensors refresh every 60 seconds.

---

## Automation examples

### Turn off the water heater during peak hours

```yaml
automation:
  - alias: "Water heater off during punta"
    trigger:
      - platform: state
        entity_id: sensor.ute_tarifas_current_period
        to: "punta"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.water_heater
```

### Turn on the dishwasher when valle begins

```yaml
automation:
  - alias: "Start dishwasher at valle"
    trigger:
      - platform: state
        entity_id: sensor.ute_tarifas_current_period
        to: "valle"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.dishwasher
```

### Notify when the next period is punta

```yaml
automation:
  - alias: "Warn before punta"
    trigger:
      - platform: state
        entity_id: sensor.ute_tarifas_next_period
        to: "punta"
    action:
      - service: notify.mobile_app
        data:
          message: >
            Punta starts at
            {{ states('sensor.ute_tarifas_next_change') | as_datetime | as_local }}.
            Consider deferring high-consumption appliances.
```

### Condition on current cost in a script

```yaml
script:
  charge_ev_if_cheap:
    alias: "Charge EV when cost is low"
    sequence:
      - condition: numeric_state
        entity_id: sensor.ute_tarifas_current_cost
        below: 7.0
      - service: switch.turn_on
        target:
          entity_id: switch.ev_charger
```

---

*← [User Manual](01-user-manual.md) · [How It Works →](03-how-it-works.md)*
