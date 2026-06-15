"""统一 ID 工具库 —— SID（Searchable ID）生成、格式化、解析。

SID 格式：{prefix}-[{category}]-{formatted_uuid}

示例：
  user-550e-8400-e29b-41d4-a716-4466-5544-0000
  asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000
  task-train-550e-8400-e29b-41d4-a716-4466-5544-0000
  log-crawl-550e-8400-e29b-41d4-a716-4466-5544-0000
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

# ── 预注册前缀常量 ──
SID_PREFIXES = {
    "user": "user",  # 用户
    "asse": "asse",  # 资产（帖子/文件/标签等所有可存储实体）
    "task": "task",  # 任务（运行时态，在内存中）
    "log": "log",  # 日志/记录
    "modr": "modr",  # 审核记录
}

# 所有注册前缀的列表，用于 parse_sid 匹配
_SID_PREFIX_LIST = list(SID_PREFIXES.keys())


@dataclass
class SidParts:
    """SID 解析结果。"""

    prefix: str  # 一级前缀，如 user, asse
    category: str | None  # 二级分类，如 post, file
    raw_hex: str  # 32 位原始 hex 字符串（无分隔符）
    uuid: uuid.UUID  # 转换后的 UUID 对象


def format_uuid(raw: uuid.UUID) -> str:
    """将 UUID 格式化为每 4 位一组、横杠分隔的 32 位 hex 字符串。

    >>> format_uuid(uuid.UUID('550e8400-e29b-41d4-a716-446655440000'))
    '550e-8400-e29b-41d4-a716-4466-5544-0000'
    """
    hex_str = raw.hex  # 32 位无分隔符 hex
    # 每 4 位一组插入横杠
    groups = [hex_str[i : i + 4] for i in range(0, 32, 4)]
    return "-".join(groups)


def make_sid(
    prefix: str,
    raw_uuid: uuid.UUID,
    category: str | None = None,
) -> str:
    """生成 SID 字符串。

    Args:
        prefix: 一级前缀（需在 SID_PREFIXES 中注册）。
        raw_uuid: UUID 对象。
        category: 二级分类（可选）。

    Returns:
        格式化的 SID 字符串。

    >>> make_sid("asse", uuid.UUID('550e8400-e29b-41d4-a716-446655440000'), "post")
    'asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000'
    >>> make_sid("user", uuid.UUID('550e8400-e29b-41d4-a716-446655440000'))
    'user-550e-8400-e29b-41d4-a716-4466-5544-0000'
    """
    if prefix not in SID_PREFIXES:
        raise ValueError(f"未知的前缀 '{prefix}'，可用前缀: {_SID_PREFIX_LIST}")

    formatted = format_uuid(raw_uuid)
    if category:
        return f"{prefix}-{category}-{formatted}"
    return f"{prefix}-{formatted}"


def parse_sid(sid: str) -> SidParts | None:
    """解析 SID 字符串，返回 SidParts；无法解析时返回 None。

    输入兼容以下格式：
      - 完整 SID:    asse-post-550e-8400-e29b-...
      - 无二级分类:   user-550e-8400-e29b-...
      - 无分隔符 hex:  asse-post-550e8400e29b...
      - 带 id: 前缀:   id:asse-post-550e-8400-...
      - 带 sid: 前缀:  sid:asse-post-550e-8400-...
      - 标准 UUID:     550e8400-e29b-41d4-a716-446655440000

    >>> p = parse_sid("asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
    >>> p.prefix, p.category
    ('asse', 'post')
    >>> p.uuid
    UUID('550e8400-e29b-41d4-a716-446655440000')
    """
    if not sid or not sid.strip():
        return None

    raw = sid.strip()

    # 1. 去除可选的 id:/sid: 前缀
    raw = re.sub(r"^(id|sid):\s*", "", raw, flags=re.IGNORECASE)

    # 2. 尝试匹配一级前缀
    prefix: str | None = None
    category: str | None = None
    rest: str = raw

    for p in _SID_PREFIX_LIST:
        # 匹配 "prefix-" 开头
        if raw.lower().startswith(p + "-"):
            prefix = p
            rest = raw[len(p) + 1 :]  # 去掉 "prefix-"
            break

    # 3. 无前缀 → 尝试直接作为 UUID 或 raw hex 解析
    if prefix is None:
        return _parse_as_raw_uuid(raw)  # type: ignore[func-returns-value]

    # 4. 有前缀，尝试提取二级分类
    #    规则：剩余部分的第一段如果是字母（且不是纯 hex），作为 category
    #    否则 category 为 None
    segments = rest.split("-")
    hex_segments_start = 0

    if segments:
        first = segments[0]
        # 如果第一段不是纯 hex（有非 hex 字符或长度不是 4 的倍数），视为 category
        if first and not _is_pure_hex_segment(first):
            category = first
            hex_segments_start = 1

    # 5. 合并剩余 hex 段
    hex_parts = segments[hex_segments_start:]
    raw_hex = "".join(hex_parts)

    # 6. 移除所有非 hex 字符
    raw_hex = _clean_hex(raw_hex)

    # 7. 验证并转换
    return _build_sid_parts(prefix, category, raw_hex)


def _parse_as_raw_uuid(raw: str) -> None:  # noqa: ARG001
    """将无前缀的输入尝试解析为 UUID/hex。无前缀时返回 None，由调用方决定如何处理。"""
    return None


def _clean_hex(text: str) -> str:
    """只保留十六进制字符 [0-9a-fA-F]。"""
    return re.sub(r"[^0-9a-fA-F]", "", text)


def _is_pure_hex_segment(seg: str) -> bool:
    """判断一段字符串是否全是 hex 字符且长度为 4 的倍数。"""
    if not seg:
        return False
    if len(seg) % 4 != 0:
        return False
    return bool(re.fullmatch(r"[0-9a-fA-F]+", seg))


def _build_sid_parts(
    prefix: str | None,
    category: str | None,
    raw_hex: str,
) -> SidParts | None:
    """从解析片段构建 SidParts，失败时返回 None。"""
    if len(raw_hex) != 32:
        return None
    try:
        uid = uuid.UUID(hex=raw_hex)
    except ValueError:
        return None
    return SidParts(prefix=prefix or "", category=category, raw_hex=raw_hex, uuid=uid)
