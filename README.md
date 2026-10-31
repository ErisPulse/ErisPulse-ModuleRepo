[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [Русский](README.ru.md)

<div align="center">

<img src="https://raw.githubusercontent.com/ErisPulse/ErisPulse/main/.github/assets/ErisPulseLogo.png" width="180" alt="ErisPulse-ModuleRepo" />

# ErisPulse-ModuleRepo

**ErisPulse module marketplace source — publish & discover modules and adapters**

<p>
  <a href="https://github.com/ErisPulse/ErisPulse/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License"></a>
  <img src="https://raw.githubusercontent.com/ErisPulse/.github/main/assets/badges/ecosystem.svg" alt="ErisPulse">
</p>

</div>

---

## Install modules

```bash
epsdk list-remote        # browse the registry
epsdk install Weather
```

Installs go through PyPI; version numbers in `packages.json` are synced from PyPI by a daily workflow — this repo only handles listing and discovery.

## Publish a module

1. Finish your module and publish it to PyPI:

   ```bash
   python -m build
   twine upload dist/*
   ```

2. Submit via the [submission issue template](https://github.com/ErisPulse/ErisPulse-ModuleRepo/issues/new?template=module_submission.md): PyPI package name, source repo, category and minimum SDK version.

3. Once approved, it gets merged into `packages.json` and becomes discoverable in the market.

Requirements: follow the ErisPulse development conventions, include docs, no licensing issues. See the [publishing guide](https://www.erisdev.com/#docs/developer-guide/publishing.md) for the full process.

## packages.json

`.github/scripts/packages_lib.py` handles all reads and writes (daily version sync, issue submissions and the web manager share it) to keep the format stable.

Top-level keys: `modules`, `adapters`, `last_updated`, `categories`. Entry order is the market display order: `"featured": true` entries first, the rest alphabetical by name.

| Field | Description |
| --- | --- |
| `package` | PyPI package name, used by the CLI for installation |
| `version` | Version, synced from PyPI by the daily workflow |
| `min_sdk_version` | Minimum SDK version — must be a bare version (e.g. `2.4.6`); operators break the SDK version check. Adapters require at least `2.7.0` |
| `repository` | Source repository URL |
| `official` / `verified` | Officially maintained / manually verified (defaults to verified) |
| `featured` | Pinned to the featured slot with a badge (optional) |
| `hidden` | When `true`, hidden from the market and excluded from stats (delisted entries are kept) |
| `category` | Category number (1 tools / 2 fun / 3 management / 4 notifications / 5 AI / 6 platform integration / 7 data analysis) — stored as a number for multilingual rendering |
| `tags` | Free-form tags used for market filters |
| `submitted_by` / `submitted_at` | Submission attribution |

> Modules and adapters can also be self-published at [workbench.erisdev.com](https://workbench.erisdev.com).

## Branches

`2x` is the default branch; `1x` archives the index from the ErisPulse v1 era.

## Links

- [Module market](https://www.erisdev.com/#market)
- [`epsdk` CLI reference](https://www.erisdev.com/#docs/user-guide/cli-reference.md)
- [Module development guide](https://www.erisdev.com/#docs/developer-guide/modules/getting-started.md)
- [ErisPulse main repo](https://github.com/ErisPulse/ErisPulse)
