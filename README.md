# UTE Tarifas

HACS custom integration for **UTE residential contracts only**.

[![HACS Default](https://img.shields.io/badge/HACS-Integration-blue)](https://hacs.xyz/) [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE) [![Release](https://img.shields.io/github/v/release/alexisml/UTE-Tarifas)](https://github.com/alexisml/UTE-Tarifas/releases/latest)

[![HACS Validation](https://github.com/alexisml/UTE-Tarifas/actions/workflows/hacs-validate.yml/badge.svg)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/hacs-validate.yml)
[![Unit Tests](https://github.com/alexisml/UTE-Tarifas/actions/workflows/tests.yml/badge.svg)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/tests.yml)
[![Tests](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Falexisml%2F7107fdc2a20719f22bc6fe9f80eba710%2Fraw%2Fev_lb_test_count.json)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/alexisml/UTE-Tarifas/graph/badge.svg)](https://codecov.io/gh/alexisml/UTE-Tarifas)
[![Ruff](https://github.com/alexisml/UTE-Tarifas/actions/workflows/ruff.yml/badge.svg)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/ruff.yml)
[![Type Check](https://github.com/alexisml/UTE-Tarifas/actions/workflows/type-check.yml/badge.svg)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/type-check.yml)
[![Spell Check](https://github.com/alexisml/UTE-Tarifas/actions/workflows/spell-check.yml/badge.svg)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/spell-check.yml)
[![CodeQL](https://github.com/alexisml/UTE-Tarifas/actions/workflows/codeql.yml/badge.svg)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/codeql.yml)
[![Gitleaks](https://github.com/alexisml/UTE-Tarifas/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/alexisml/UTE-Tarifas/actions/workflows/gitleaks.yml)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-brightgreen?logo=dependabot)](https://github.com/alexisml/UTE-Tarifas/blob/main/.github/dependabot.yml)
[![Lines of Code](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Falexisml%2F7107fdc2a20719f22bc6fe9f80eba710%2Fraw%2Fev_lb_loc.json)](https://github.com/alexisml/UTE-Tarifas)

## Features

- Residential tariff support: **simple**, **double**, and **triple**.
- User-configurable schedules for workdays, weekends, and national holidays.
- Date-bounded pricing tables (`start` / `end`) so historical/future rates are handled.
- Sensors:
  - current cost (`UYU/kWh`)
  - current tariff period enum (`simple`, `valle`, `llano`, `punta`)
  - next expected cost change timestamp
  - next period enum
  - selected residential contract type

## Notes

- This integration intentionally targets **residential UTE contracts only**.
- National holidays are resolved using the configured country code (default: `UY`).
