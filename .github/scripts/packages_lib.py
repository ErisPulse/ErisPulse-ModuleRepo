#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
packages.json 规范化读写工具（唯一写入口）

所有会修改 packages.json 的脚本都必须经 :func:`write_packages` 落盘，
以保证文件长期保持一致：

1. **排列方式**：先推荐位、再字母序。
   - 条目带 ``featured: true`` 者置顶，内部顺序由 :data:`FEATURED_PRIORITY` 决定
     （未列入该表但标了 ``featured`` 的，按字母序排在已列出者之后）；
   - 其余条目按名称字典序（大小写不敏感）排序；
   - 顶层分类顺序固定为 modules → adapters → cli_extensions。
2. **条目结构**：字段顺序固定为 :data:`ENTRY_FIELD_ORDER`；
   未声明的自定义字段按原相对顺序追加到末尾（不丢字段，向后兼容）。
3. **值规范化**：``min_sdk_version`` 去掉 ``>=`` ``^`` ``v`` 等前缀，
   统一为裸版本号（SDK 的 ``parse_version`` 无法解析带运算符的字符串，
   会导致版本检查静默放行），并按 :data:`CATEGORY_MIN_SDK_FLOOR`
   补全 / 抬高到分类最低版本（适配器一律不低于 ``2.7.0``）。
4. **分类**：``category`` 是受控字段（编号），取值见 :data:`CATEGORY_TAXONOMY`，
   经 :func:`normalize_category` 归一化，编号无法识别时不写回索引；
   词表随后写入 packages.json 顶层 ``categories``（``{"1": "tool", ...}``），
   供官网提交表单、筛选面板与卡片徽章渲染本地化名称。
5. **标签**：``tags`` 是自由文本，仅经 :func:`normalize_tags` 做卫生处理
   （去空白、去空项、大小写不敏感去重、截断到 :data:`TAG_MAX` 个），
   仓库侧不限制标签内容，也不与任何词表匹配。

兼容性说明：JSON 对象的键顺序对任何解析器都不具备语义，
SDK CLI、Cloudflare Worker、官网 market 均以字典/对象读取，
因此重排只影响展示顺序，不会破坏既有调用方；
``featured`` 为新增可选字段，现有消费方读取时均按白名单取值，会直接忽略。
"""

import json
import re
from pathlib import Path

# 分类容器顺序（与既有文件一致，便于人工阅读与 diff）
CATEGORY_ORDER = ("modules", "adapters", "cli_extensions")

# 推荐位顺序：名称按此处顺序置顶展示，人工维护
#
# 用法：
#   1. 在条目上加 ``"featured": true`` —— 该模块进入推荐位（这是消费方唯一可见的标记）
#   2. 若需指定推荐位内部先后，把名称按期望顺序插入本元组
#
# 未列入本元组但标了 featured 的条目，按字母序排在已列出者之后；
# 本元组中不存在于 packages.json 的名称会被自动忽略（不会产生悬空引用）。
FEATURED_PRIORITY = (
    "Dashboard",
    "HelpModule",
    "HelpNext",
    "Takumi",
    "Cron",
)

# 条目字段的标准顺序；未列出的字段按原相对顺序追加到末尾
ENTRY_FIELD_ORDER = (
    "package",
    "version",
    "author",
    "description",
    "min_sdk_version",
    "repository",
    "official",
    "verified",
    "featured",
    "hidden",
    "category",
    "tags",
    "submitted_by",
    "submitted_by_uid",
    "oauth_provider",
    "submitted_at",
)

# 分类最低 SDK 版本地板：字段缺失即补全，低于则抬高，高于则保持（只抬不降）
#
# 适配器接口自 SDK 2.7.0 起稳定，故适配器一律要求 >= 2.7.0。
# 该项必须由脚本保证而非依赖人工填写：CLI 的安装兼容性检查以
# ``"min_sdk_version" in package_info`` 为前提，字段缺失时检查被完全跳过，
# 等于该适配器没有版本门槛。
CATEGORY_MIN_SDK_FLOOR = {
    "adapters": "2.7.0",
}

# ── 标签 ──
#
# 标签是自由文本：作者可以用中文、英文或自己的写法表达模块，仓库侧不做
# 词表匹配。历史上曾按受控词表硬匹配，结果是作者写的 ``视频`` / ``parser``
# 这类标签被直接丢弃 —— 属于数据损失，且用户无法在提交表单里表达新概念。
#
# 因此这里只做卫生处理，不判断「应该叫什么」：
#   1. 去首尾空白，把连续空白折成单个空格；
#   2. 丢弃空项与非字符串项；
#   3. 大小写不敏感去重（``AI`` 与 ``ai`` 视为同一个，保留先出现的写法）；
#   4. 截断到 :data:`TAG_MAX` 个。
#
# 字符规则（允许的字符、单个标签长度）由提交入口把关（Cloudflare Worker 的
# ``TAG_RE``），仓库侧不重复校验：这里既要处理历史数据，也要处理来自
# Worker 的数据，两边的上限保持一致即可。
TAG_MAX = 20

# 单个标签最长字符数：与 Worker 入口的 TAG_RE 上限一致
TAG_LENGTH_MAX = 50

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_tags(tags):
    """
    宽松归一化标签列表：去空白 → 去空项 → 大小写不敏感去重 → 截断

    保留作者书写顺序与原始大小写（``AI`` 不会被改写成 ``ai``），
    只保证落进 packages.json 的内容干净、可用于官网筛选。

    :param tags: 原始标签列表（非列表一律返回空列表）
    :return: 归一化后的标签列表
    """
    if isinstance(tags, str) or not isinstance(tags, (list, tuple)):
        return []

    normalized = []
    seen = set()
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = _WHITESPACE_RE.sub(" ", tag).strip()[:TAG_LENGTH_MAX]
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)

    return normalized[:TAG_MAX]


# ── 模块分类（受控字段）──
#
# 标签自由，分类受控：分类是枚举，用于官网的类型筛选与卡片徽章。
# 索引里存编号而不是名字，是为了面向多语言 —— 前端按当前语言取
# ``category.<key>`` 的文案渲染（见 assets/js/i18n.js），
# 后端（Worker 校验、GitHub Actions、CLI）只认编号。
#
# 因此编号是契约：调整分类必须同时迁移 packages.json 里已有的取值，
# 并同步前端 config.js 的 MODULE_CATEGORIES 与 Worker 的白名单。
CATEGORY_TAXONOMY = (
    (1, "tool"),        # 工具
    (2, "fun"),         # 娱乐
    (3, "admin"),       # 管理
    (4, "notify"),      # 通知
    (5, "ai"),          # AI
    (6, "platform"),    # 平台对接
    (7, "analytics"),   # 数据分析
)

# 合法分类编号
CATEGORY_IDS = tuple(category_id for category_id, _key in CATEGORY_TAXONOMY)

# 语义名 → 编号（允许以语义名提交，落盘一律为编号）
CATEGORY_BY_KEY = {key: category_id for category_id, key in CATEGORY_TAXONOMY}


def normalize_category(value):
    """
    将分类归一化为编号

    接受编号、纯数字字符串、语义名（如 ``"tool"``）。

    :param value: 原始分类值
    :return: 分类编号（int）；无法识别时返回 None
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value in CATEGORY_IDS else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return normalize_category(int(text))
        return CATEGORY_BY_KEY.get(text.casefold())
    return None


DEFAULT_PACKAGES_FILE = "packages.json"

# 版本约束运算符 / 前缀：>=2.4.6、^2.4.6、v2.4.6、=2.4.6 → 2.4.6
_VERSION_PREFIX_RE = re.compile(r"^\s*(?:>=|<=|==|!=|~=|>|<|=|\^|v)\s*")

# 推荐位名称 → 优先级序号（大小写不敏感）
_FEATURED_RANK = {
    name.casefold(): index for index, name in enumerate(FEATURED_PRIORITY)
}


def entry_sort_key(item):
    """
    排列键：推荐位优先，其余按名称字典序

    :param item: ``(name, entry)`` 键值对
    :return: tuple 可直接用于 sorted() 的比较键
    """
    name, entry = item
    key = str(name)
    folded = key.casefold()

    if not (isinstance(entry, dict) and entry.get("featured")):
        # 非推荐位：排在所有推荐位之后
        return (1, 0, folded, key)

    # 推荐位：FEATURED_PRIORITY 中未列出的统一排到已列出者之后，再按字母序
    return (0, _FEATURED_RANK.get(folded, len(FEATURED_PRIORITY)), folded, key)


def normalize_min_sdk_version(value):
    """
    将 ``min_sdk_version`` 规范化为裸版本号

    :param value: 原始值（如 ``">=2.4.6"``）
    :return: 规范化后的字符串；非字符串或空值原样返回
    """
    if not isinstance(value, str):
        return value
    normalized = _VERSION_PREFIX_RE.sub("", value).strip()
    return normalized or value


def _parse_version_tuple(value):
    """
    将版本号解析为可比较的整数元组

    :param value: 版本号字符串（如 ``"2.7.0"``）
    :return: tuple[int, ...]；无法解析时返回 None
    """
    text = normalize_min_sdk_version(value)
    if not isinstance(text, str) or not text:
        return None
    parts = text.split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def apply_min_sdk_floor(entry, floor):
    """
    对条目施加分类最低 SDK 版本地板（只抬不降）

    缺失、为空或无法解析的声明一律补为 ``floor``；低于 ``floor`` 的抬高到
    ``floor``；高于 ``floor`` 的保持原值（不虚报兼容性）。

    :param entry: 条目字典（原地写入 ``min_sdk_version``）
    :param floor: 分类最低版本号；空值表示不限
    :return: 传入的条目字典
    """
    floor_key = _parse_version_tuple(floor)
    if not isinstance(entry, dict) or floor_key is None:
        return entry

    current = _parse_version_tuple(entry.get("min_sdk_version"))
    if current is None or current < floor_key:
        entry["min_sdk_version"] = floor
    return entry


def normalize_entry(entry, min_sdk_floor=None):
    """
    规范化单个包条目：固定字段顺序 + 规范化字段值

    :param entry: 原始条目字典
    :param min_sdk_floor: 分类最低 SDK 版本（见 :data:`CATEGORY_MIN_SDK_FLOOR`），
        None 表示不限
    :return: 新字典（不修改入参），未知字段保持在末尾
    """
    if not isinstance(entry, dict):
        return entry

    if min_sdk_floor:
        # 先补全/抬高，再投影字段顺序，保证新增的 min_sdk_version 落在标准位置
        entry = apply_min_sdk_floor(dict(entry), min_sdk_floor)

    result = {}
    for key in ENTRY_FIELD_ORDER:
        if key in entry:
            value = entry[key]
            if key == "min_sdk_version":
                value = normalize_min_sdk_version(value)
            elif key == "category":
                # 分类是受控字段：编号无法识别时不写回索引，
                # 避免污染前端渲染（提交入口会先行拒绝非法分类）
                value = normalize_category(value)
                if value is None:
                    continue
            elif key == "tags":
                value = normalize_tags(value)
            result[key] = value

    for key, value in entry.items():
        if key not in result:
            result[key] = value

    return result


def normalize_packages(data):
    """
    规范化整个 packages.json：顶层层级顺序 + 分类内名称排序 + 条目结构

    :param data: 已解析的 packages.json 内容
    :return: 新字典（不修改入参）
    """
    if not isinstance(data, dict):
        return data

    result = {}
    if "last_updated" in data:
        result["last_updated"] = data["last_updated"]

    # 分类词表随索引一起发布：官网提交表单 / 筛选面板 / 卡片徽章据此渲染，
    # 避免前后端各自硬编码一份编号表（这里只发布编号 → 语义名，
    # 具体语言的展示名由前端 i18n 的 category.<key> 提供）
    result["categories"] = {
        str(category_id): key for category_id, key in CATEGORY_TAXONOMY
    }

    for category in CATEGORY_ORDER:
        items = data.get(category)
        if not isinstance(items, dict):
            continue
        floor = CATEGORY_MIN_SDK_FLOOR.get(category)
        result[category] = {
            name: normalize_entry(entry, floor)
            for name, entry in sorted(items.items(), key=entry_sort_key)
        }

    # 保底：未来新增的顶层字段不丢失
    for key, value in data.items():
        if key not in result:
            result[key] = value

    return result


def dumps(data):
    """
    将数据序列化为 packages.json 的规范文本

    :param data: 待序列化数据
    :return: JSON 文本（UTF-8 可读、缩进 4 空格）
    """
    return json.dumps(data, ensure_ascii=False, indent=4)


def write_packages(path=DEFAULT_PACKAGES_FILE, data=None):
    """
    规范化并写入 packages.json

    :param path: 目标文件路径（默认 ``packages.json``）
    :param data: 待写入数据；为 None 时从 ``path`` 读取后规范化写回
    :return: 规范化后的数据
    """
    target = Path(path)
    if data is None:
        data = json.loads(target.read_text(encoding="utf-8"))

    normalized = normalize_packages(data)
    # 显式 LF：仓库索引为 LF，避免在 Windows 上写出 CRLF 造成换行噪音
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(normalized))
    return normalized


if __name__ == "__main__":
    import sys

    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PACKAGES_FILE
    write_packages(file_path)
    print(f"normalized: {file_path}")
