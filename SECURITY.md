# Security Policy

## Supported versions

Only the latest release receives security fixes. Older versions are not maintained.

| Version | Supported |
|---------|-----------|
| Latest  | ✅ Yes    |
| Older   | ❌ No     |

---

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security vulnerabilities using [GitHub's private vulnerability reporting](https://github.com/alexisml/UTE-Tarifas/security/advisories/new). This keeps the disclosure private until a fix is available.

Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept (if safe to share)
- Any suggested mitigations you are aware of

You will receive an acknowledgement within **7 days**. If the vulnerability is confirmed, a fix will be prioritized and a public advisory published after the patch is released.

---

## Scope

This integration is a **calculated tariff sensor** for Home Assistant. It reads the current time, applies the user's configured schedule, and exposes pricing information — it does not control any hardware or send any commands. Security issues in scope include:

- Sensitive data exposure through logs or entities
- Incorrect tariff calculation that could mislead energy-cost decisions
- Dependency vulnerabilities in packages listed in `pyproject.toml` or `custom_components/ute_tarifas/manifest.json`

Issues related to the Home Assistant platform itself are out of scope — please report those to the relevant upstream projects.

---

## Disclosure policy

We follow a **coordinated disclosure** model:

1. Reporter submits a private vulnerability report.
2. Maintainer acknowledges within 7 days.
3. Fix is developed and tested privately.
4. Fix is released; a public GitHub Security Advisory is published.
5. Reporter is credited in the advisory (unless they prefer to remain anonymous).

---

## AI disclosure

Parts of this project were developed with AI assistance. If you identify a vulnerability that appears to be a class of error commonly introduced by AI-generated code (e.g. incorrect time-range boundary handling, insecure defaults), please report it so patterns can be identified and corrected.
