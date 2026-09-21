<div align="center">

<img src=".github/assets/ErisPulseLogo.png" width="180" alt="ErisPulse-ModuleRepo" />

# ErisPulse-ModuleRepo

**ErisPulse 模块源仓库 —— 贡献并发布你的模块 / 适配器 / CLI 扩展。**

<p>
  <a href="https://github.com/ErisPulse/ErisPulse-ModuleRepo"><img src="https://img.shields.io/github/stars/ErisPulse/ErisPulse-ModuleRepo?style=for-the-badge&logo=github&color=brightgreen" alt="Stars"></a>
  <a href="https://github.com/ErisPulse/ErisPulse"><img src="https://img.shields.io/badge/Powered_by-ErisPulse-FF6B9D?style=for-the-badge&logo=bookstack&logoColor=white" alt="ErisPulse"></a>
</p>

</div>

---

当前 2x 分支为默认分支，1x 分支为归档版本。

我们欢迎社区成员贡献新的模块！提出 issue 可以添加您的模块/适配器/CLI 拓展到库中。

## 贡献模块

我们采用 PyPI 包的方式管理模块。贡献者只需将模块发布到 PyPI，然后通过 issue 提交相关信息即可。

### 贡献要求

请确保满足以下要求：
- 模块代码符合 ErisPulse 开发规范
- 提供完整的文档和使用说明
- 确保无版权问题，允许我们修改与发布
- 模块已在 PyPI 发布

### 提交流程

1. **将模块发布到 PyPI**

   使用 `twine` 或其他工具将您的 Python 包发布到 PyPI：
   ```bash
   python -m build
   twine upload dist/*
   ```

2. **提交 Issue**

   访问仓库的 Issues 页面，使用"模块/适配器/CLI扩展提交"模板创建一个新的 issue，填写以下信息：
   
   - **提交类型**：模块 (Module)、适配器 (Adapter) 或 CLI 扩展 (CLI Extension)
   - **基本信息**：名称、描述、作者、仓库地址
   - **技术信息**：最低 SDK 版本要求、依赖项
   - **PyPI 包名**：确保已在 PyPI 发布
   - **其他信息**：分类、标签、是否官方维护等

3. **审核与合并**

   我们将审核您的提交。审核通过后，会将您的模块信息添加到 `packages.json` 中，使其可以被 ErisPulse 生态系统发现和使用。

### 检查清单

在提交前，请确认：
- [ ] 代码遵循 ErisPulse 开发规范
- [ ] 包含适当的文档
- [ ] 包含测试用例（如适用）
- [ ] 已在 PyPI 发布

---

## 数据结构约定

`packages.json` 由 `.github/scripts/packages_lib.py` 统一读写，每日版本更新、Issue 提交、网页端管理三条链路都经它落盘，以保证格式稳定。

### 排列顺序

分类内的条目顺序 **就是官网模块市场的展示顺序**（前端不做二次排序），规则为：

1. **推荐位**：条目带 `"featured": true` 者置顶，内部先后由 `packages_lib.py` 的 `FEATURED_PRIORITY` 决定
2. **其余条目**：按名称字母序（大小写不敏感）排列

> 想推荐一个模块：给它的条目加 `"featured": true` 即可；若还要指定推荐位内部的先后，再把名称按期望顺序加入 `FEATURED_PRIORITY`。未列入该元组的推荐模块，会按字母序排在已列出者之后（元组中不存在的名称会被自动忽略）。

### 分组与字段

顶层分组（JSON 顶层键）：`modules`、`adapters`、`cli_extensions`（预留，当前为空且 SDK 未读取）。
另有 `categories` 键随索引发布分类词表（编号 → 语义名），供官网提交表单与筛选面板渲染本地化名称。

> 注意区分两个「分类」：顶层分组是**索引容器的结构**（模块 / 适配器 / CLI 扩展）；
> 条目里的 `category` 是**模块类型分类**（工具、娱乐、管理……）。

| 字段 | 说明 |
| --- | --- |
| `package` | PyPI 包名，CLI 安装的依据 |
| `version` | 版本号，由每日工作流从 PyPI / GitHub Release 同步 |
| `min_sdk_version` | 最低 SDK 版本，**必须是裸版本号**（如 `2.4.6`）；带 `>=` 等运算符会导致 SDK 版本检查静默失效。适配器另有 `2.7.0` 下限 |
| `repository` | 源码仓库地址 |
| `official` | 是否官方维护 |
| `verified` | 是否已人工验证；**缺省视为 true**（SDK 与官网均按此约定） |
| `featured` | 是否进入推荐位（可选，缺省不推荐）：排序置顶，且市场展示「推荐」角标 |
| `hidden` | 为 `true` 时不在模块市场展示（下架但保留条目），同时不计入市场统计 |
| `category` | **受控字段**：模块分类编号，取值见 `packages_lib.py` 的 `CATEGORY_TAXONOMY`（1 工具 / 2 娱乐 / 3 管理 / 4 通知 / 5 AI / 6 平台对接 / 7 数据分析）。存编号而不是名字是为了多语言：官网按当前语言渲染展示名。编号无法识别时不会写回索引 |
| `tags` | **自由文本**标签，中英文皆可，仓库侧不限制内容（仅去空白、大小写不敏感去重、最多 20 个）；市场据此生成标签筛选（多选取交集，多选分类取并集） |
| `submitted_by` / `submitted_by_uid` / `oauth_provider` | 提交者溯源信息，网页端凭 `uid` 校验模块归属 |
| `submitted_at` | 提交时间（ISO 8601，UTC） |

字段顺序由 `packages_lib.py` 的 `ENTRY_FIELD_ORDER` 固定，未声明的自定义字段会保留并追加到条目末尾。

标签与分类的分工是**标签自由、分类受控**：

- 标签交给作者表达，不设词表、不做匹配（只清理空白与重复、限制数量）。因此市场筛选面板里的标签集合是**数据驱动**的，新标签提交后会自动出现在面板里
- 分类是枚举，用于官网的类型筛选与卡片徽章。编号是前后端契约，改动需同时迁移索引文件中已有的取值，并同步 `packages_lib.py` 的 `CATEGORY_TAXONOMY`、前端 `assets/js/config.js` 的 `MODULE_CATEGORIES` 与 Worker 的白名单

### 最低 SDK 版本

`min_sdk_version` 的规范与下限同样由 `packages_lib.py` 保证：

- 必须是**裸版本号**（如 `2.4.6`）。`>=2.4.6`、`^2.4.6`、`v2.4.6` 等会被自动剥离前缀——带运算符的字符串会让 SDK 的版本解析失败，导致兼容性检查静默放行
- **适配器一律不低于 `2.7.0`**：字段缺失、为空或低于该值时由脚本补全 / 抬高；声明高于该值的保持原值（不虚报兼容性），见 `CATEGORY_MIN_SDK_FLOOR`
- 分类下限只在此一处维护，三条写入链路（每日更新、Issue 提交、网页端编辑）自动生效

> 为什么必须由脚本兜底：CLI 的安装兼容性检查以"字段存在"为前提（`if "min_sdk_version" in package_info`），字段缺失时检查会被**完全跳过**，等于该组件没有版本门槛。

---

## 感谢您的支持与贡献！
