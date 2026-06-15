"""爬虫插件 —— 种子管理器：种子池、黑白名单、探嗅收录。"""

from __future__ import annotations

from urllib.parse import urlparse

from backend.core.container import ServiceContainer


class SeedManager:
    """种子管理器：管理种子池、黑白名单、探嗅后收录/拒绝。"""

    def __init__(self, container: ServiceContainer):
        self.container = container
        self._seeds: list[str] = []
        self._seen: set[str] = set()
        self._blacklist: list[str] = []  # 域名或 URL 模式
        self._whitelist: list[str] = []  # 优先收录

    async def initialize(self) -> None:
        """从环境变量读初始种子。"""
        config = self.container.get("config")
        seeds_env = config.get("CRAWLER_SEEDS", "") if config else ""
        if seeds_env:
            for url in seeds_env.split(","):
                url = url.strip()
                if url:
                    self.add_seed(url, source="env")

    def add_seed(self, url: str, source: str = "manual") -> bool:  # noqa: ARG002
        """添加种子，返回是否成功。"""
        normalized = self._normalize(url)
        if not normalized:
            return False
        if normalized in self._seen:
            return False
        if self.is_blacklisted(normalized):
            return False
        self._seeds.append(normalized)
        self._seen.add(normalized)
        return True

    def pop_seed(self) -> str | None:
        """取出一个种子（FIFO）。"""
        if self._seeds:
            return self._seeds.pop(0)
        return None

    def is_blacklisted(self, url: str) -> bool:
        """检查 URL 是否在黑名单中（按主机名/规范化 URL 前缀匹配，避免子串误匹配）。"""
        host = self._get_hostname(url)
        if not host:
            return False
        normalized = self._normalize(url) or ""
        for pattern in self._blacklist:
            if self._url_rule_matches(normalized, host, pattern):
                return True
        return False

    def is_whitelisted(self, url: str) -> bool:
        """检查 URL 是否在白名单中。"""
        host = self._get_hostname(url)
        if not host:
            return False
        normalized = self._normalize(url) or ""
        for pattern in self._whitelist:
            if self._url_rule_matches(normalized, host, pattern):
                return True
        return False

    def add_to_blacklist(self, pattern: str, reason: str = "") -> None:  # noqa: ARG002
        """添加黑名单规则。"""
        if pattern not in self._blacklist:
            self._blacklist.append(pattern)

    def add_to_whitelist(self, pattern: str) -> None:
        """添加白名单规则。"""
        if pattern not in self._whitelist:
            self._whitelist.append(pattern)

    def get_blacklist(self) -> list[str]:
        return list(self._blacklist)

    def get_whitelist(self) -> list[str]:
        return list(self._whitelist)

    def process_sniff_result(self, url: str, sniff_result: dict) -> bool:
        """探嗅后处理：有意义的收录为种子，无意义的加入黑名单。"""
        if sniff_result.get("is_functional", False):
            self.add_to_blacklist(self._get_hostname(url), reason="functional_page")
            return False
        if not sniff_result.get("has_content", False):
            return False
        return self.add_seed(url, source="sniff")

    def discover_seeds_from_links(self, links: list[str], source_url: str) -> list[str]:  # noqa: ARG002
        """从页面链接中发现新种子。"""
        new_seeds = []
        for link in links:
            normalized = self._normalize(link)
            if not normalized:
                continue
            if normalized in self._seen:
                continue
            if self.is_blacklisted(normalized):
                continue
            self._seen.add(normalized)
            self._seeds.append(normalized)
            new_seeds.append(normalized)
        return new_seeds

    @property
    def queue_size(self) -> int:
        return len(self._seeds)

    @property
    def total_seen(self) -> int:
        return len(self._seen)

    @staticmethod
    def _normalize(url: str) -> str | None:
        """规范化 URL。"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/') or '/'}"  # noqa: E501
        except Exception:
            return None

    @staticmethod
    def _get_hostname(url: str) -> str:
        try:
            return (urlparse(url).hostname or "").lower()
        except Exception:
            return ""

    @staticmethod
    def _url_rule_matches(normalized: str, host: str, pattern: str) -> bool:
        """规则：完整 http(s) URL 则做规范化前缀匹配；否则按主机或 host/path 匹配。"""
        p = pattern.strip()
        if not p:
            return False
        pl = p.lower()
        if pl.startswith("http://") or pl.startswith("https://"):
            prefix = SeedManager._normalize(pl)
            return bool(prefix and normalized.startswith(prefix))
        if "/" in pl:
            dom, _, rest = pl.partition("/")
            dom = dom.strip().lower()
            if not dom or not (host == dom or host.endswith("." + dom)):
                return False
            if not rest:
                return True
            try:
                path = urlparse(normalized).path or "/"
            except Exception:
                return False
            return path.startswith("/" + rest)
        dom = pl
        return host == dom or host.endswith("." + dom)
