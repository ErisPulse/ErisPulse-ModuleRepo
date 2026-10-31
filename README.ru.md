[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [Русский](README.ru.md)

<div align="center">

<img src="https://raw.githubusercontent.com/ErisPulse/ErisPulse/main/.github/assets/ErisPulseLogo.png" width="180" alt="ErisPulse-ModuleRepo" />

# ErisPulse-ModuleRepo

**Исходный репозиторий маркетплейса модулей ErisPulse**

<p>
  <a href="https://github.com/ErisPulse/ErisPulse/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License"></a>
  <img src="https://raw.githubusercontent.com/ErisPulse/.github/main/assets/badges/ecosystem.svg" alt="ErisPulse">
</p>

</div>

---

社区模块与适配器收录在 [`packages.json`](packages.json)，[模块市场](https://www.erisdev.com/#market)在线展示，`epsdk install` 一条命令安装。

## 安装模块

```bash
epsdk list-remote        # 浏览远端收录
epsdk install Weather
```

安装走 PyPI；`packages.json` 中的版本号由每日工作流从 PyPI 同步，本仓库只负责收录与发现。

## 发布模块

1. 模块开发完成并发布到 PyPI：

   ```bash
   python -m build
   twine upload dist/*
   ```

2. 用[收录 Issue 模板](https://github.com/ErisPulse/ErisPulse-ModuleRepo/issues/new?template=module_submission.md)提交：PyPI 包名、源码仓库、分类与最低 SDK 版本。

3. 审核通过后合入 `packages.json`，市场即可发现。

要求：遵循 ErisPulse 开发规范、附文档、无版权问题。完整流程见[发布指南](https://www.erisdev.com/#docs/developer-guide/publishing.md)。

## packages.json

`.github/scripts/packages_lib.py` 统一读写（每日版本更新、Issue 提交、网页端管理三条链路共用），保证格式稳定。

顶层键：`modules`、`adapters`、`last_updated`、`categories`。条目顺序即市场展示顺序：带 `"featured": true` 的置顶，其余按名称字母序。

| 字段 | 说明 |
| --- | --- |
| `package` | PyPI 包名，CLI 安装的依据 |
| `version` | 版本号，由每日工作流从 PyPI 同步 |
| `min_sdk_version` | 最低 SDK 版本，必须是裸版本号（如 `2.4.6`），带运算符会导致 SDK 版本检查失效；适配器不低于 `2.7.0` |
| `repository` | 源码仓库地址 |
| `official` / `verified` | 是否官方维护 / 已人工验证（缺省视为已验证） |
| `featured` | 进入推荐位并展示「推荐」角标（可选） |
| `hidden` | `true` 时不在市场展示且不计入统计（下架保留条目） |
| `category` | 模块分类编号（1 工具 / 2 娱乐 / 3 管理 / 4 通知 / 5 AI / 6 平台对接 / 7 数据分析），存编号以支持多语言渲染 |
| `tags` | 自由文本标签，市场据此生成筛选 |
| `submitted_by` / `submitted_at` | 提交者溯源信息 |

## 分支

`2x` 为默认分支，`1x` 归档 ErisPulse v1 时代的索引。

## 相关链接

- [模块市场](https://www.erisdev.com/#market)
- [`epsdk` 命令参考](https://www.erisdev.com/#docs/user-guide/cli-reference.md)
- [模块开发入门](https://www.erisdev.com/#docs/developer-guide/modules/getting-started.md)
- [ErisPulse 主仓库](https://github.com/ErisPulse/ErisPulse)
