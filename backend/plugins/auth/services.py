"""认证插件 —— 用户认证服务：CRUD、密码验证、JWT 签发/验证。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import func, select

from backend.core.middleware import AppError, AuthError
from backend.core.rate_limiter import RateLimiter


class AuthService:
    """认证服务：用户注册/登录/登出/token 管理。"""

    def __init__(self, container):
        self.container = container
        db = container.get("db")
        self.session_factory = db["session_factory"]
        self.secret_key = container.get("config").get_required("SECRET_KEY")
        # token 有效期：access_token 2 小时，refresh_token 7 天
        self.access_token_expire_hours = 2
        self.refresh_token_expire_days = 7
        # 登录限流：每 IP+identity 每分钟最多 5 次尝试
        self._login_limiter = RateLimiter(max_attempts=5, window_seconds=60)
        # Token 黑名单：{jti: expiry_timestamp}，内存实现
        self._token_blacklist: dict[str, float] = {}

    # --- 用户注册 ---
    async def register(
        self, email: str, username: str, nickname: str, password: str, level: int = 5
    ) -> dict:
        """注册新用户。第一个注册用户自动成为 P0（最高权限），后续默认 P5。"""
        from backend.plugins.auth.models import (
            NicknameBlacklist,
            User,
            UserSettings,
        )

        # email 格式简单校验
        if "@" not in email or not email.strip():
            raise AppError("邮箱格式不正确", code="invalid_email", status_code=400)
        email = email.strip().lower()

        async with self.session_factory() as session:
            # 检查邮箱是否已存在
            result = await session.execute(
                select(User).where(func.lower(User.email) == email)
            )
            if result.scalar_one_or_none():
                raise AppError("邮箱已被使用", code="email_exists", status_code=409)

            # 检查用户名是否已存在
            result = await session.execute(
                select(User).where(User.username == username)
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise AppError("用户名已存在", code="username_exists", status_code=409)

            # 检查昵称是否在黑名单中
            if nickname:
                blacklist_result = await session.execute(
                    select(NicknameBlacklist).where(
                        func.lower(NicknameBlacklist.keyword)
                        == nickname.strip().lower()
                    )
                )
                if blacklist_result.scalar_one_or_none():
                    raise AppError(
                        "昵称包含敏感词", code="nickname_blocked", status_code=400
                    )

            # 第一个注册用户自动成为 P0
            count_result = await session.execute(select(func.count(User.id)))
            is_first_user = count_result.scalar() == 0
            effective_level = 0 if is_first_user else level

            # 密码 hash
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            user_id = uuid.uuid4()
            user = User(
                id=user_id,
                email=email,
                username=username,
                nickname=nickname,
                password_hash=password_hash,
                level=effective_level,
            )
            user.generate_sid("user")
            session.add(user)

            # 创建默认用户设置
            settings = UserSettings(user_id=user_id)
            session.add(settings)

            # 第一个用户（P0）预填所有页面权限
            if is_first_user:
                from backend.plugins.auth.models import PageComponentPermission

                all_pages = [
                    "home",
                    "explore",
                    "create",
                    "assets",
                    "scheduler",
                    "profile",
                    "posts",
                    "creator",
                    "console",
                    "admin_users",
                    "admin_content",
                    "admin_ops",
                    "admin_permissions",
                    "tasks",
                    "ip_ban",
                ]
                for page_name in all_pages:
                    session.add(
                        PageComponentPermission(
                            level=0,
                            page_name=page_name,
                            component_name="page",
                            visible=True,
                        )
                    )

            await session.commit()
            await session.refresh(user)

            # 签发 token
            access_token = self._create_token(
                user, expires_hours=self.access_token_expire_hours
            )
            refresh_token = self._create_token(
                user, expires_days=self.refresh_token_expire_days
            )

            return {
                "user": self._user_to_dict(user),
                "access_token": access_token,
                "refresh_token": refresh_token,
            }

    # --- 用户登录 ---
    async def login(self, identity: str, password: str, client_ip: str = "") -> dict:
        """验证邮箱或用户名+密码，返回 JWT token。"""
        from backend.plugins.auth.models import LoginHistory, User

        # 暴力破解防护：基于 identity + IP 的限流检查
        limiter_key = f"{identity}-{client_ip}" if client_ip else identity
        if self._login_limiter.is_limited(limiter_key):
            raise AppError(
                "登录尝试次数过多，请 60 秒后再试",
                code="rate_limited",
                status_code=429,
            )

        async with self.session_factory() as session:
            # 先按 email 查，再按 username 查
            result = await session.execute(
                select(User).where(
                    (func.lower(User.email) == identity.lower())
                    | (User.username == identity)
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                self._login_limiter.record_attempt(limiter_key)
                raise AuthError("邮箱/用户名或密码错误")

            # 验证密码
            if not bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                self._login_limiter.record_attempt(limiter_key)
                raise AuthError("邮箱/用户名或密码错误")

            if not user.is_active:
                self._login_limiter.record_attempt(limiter_key)
                raise AuthError("账号已被禁用，请联系管理员")

            # 登录成功，重置限流计数
            self._login_limiter.reset(limiter_key)

            # 记录登录历史和审计字段
            now = datetime.now(timezone.utc)
            login_history = LoginHistory(
                user_id=user.id,
                ip=client_ip,
            )
            session.add(login_history)

            user.login_count = (user.login_count or 0) + 1
            user.last_login_at = now
            user.last_login_ip = client_ip

            access_token = self._create_token(
                user, expires_hours=self.access_token_expire_hours
            )
            refresh_token = self._create_token(
                user, expires_days=self.refresh_token_expire_days
            )

            await session.commit()
            await session.refresh(user)

            return {
                "user": self._user_to_dict(user),
                "access_token": access_token,
                "refresh_token": refresh_token,
            }

    # --- 登出 ---
    async def logout(self, token: str) -> None:
        """登出：将 token 的 jti 加入黑名单，使其立即失效。"""
        self._cleanup_blacklist()
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
            exp = payload.get("exp", 0)
            if jti:
                self._token_blacklist[jti] = exp
        except jwt.InvalidTokenError:
            pass  # 无效 token 无需加入黑名单

    def is_token_blacklisted(self, jti: str) -> bool:
        """检查 token 的 jti 是否在黑名单中。"""
        self._cleanup_blacklist()
        return jti in self._token_blacklist

    def _cleanup_blacklist(self) -> None:
        """清理已过期的黑名单条目（懒清理）。"""
        now = datetime.now(timezone.utc).timestamp()
        expired = [jti for jti, exp in self._token_blacklist.items() if exp < now]
        for jti in expired:
            self._token_blacklist.pop(jti, None)

    # --- 获取当前用户 ---
    async def get_user_by_id(self, user_id: uuid.UUID) -> dict | None:
        """根据 ID 获取用户信息。"""
        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                return self._user_to_dict(user)
            return None

    # --- Token 刷新 ---
    async def refresh_token(self, refresh_token: str) -> dict:
        """使用 refresh token 换取新的 access token。"""
        payload = self._verify_token(refresh_token)
        user_id = uuid.UUID(payload["sub"])

        user = await self.get_user_by_id(user_id)
        if not user:
            raise AuthError("用户不存在")

        # 从 payload 构造用户数据用于签发新 token
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=self.access_token_expire_hours)
        new_payload = {
            "sub": user["id"],
            "level": user["level"],
            "blog_quality_level": user["blog_quality_level"],
            "exp": exp,
        }
        new_access_token = jwt.encode(new_payload, self.secret_key, algorithm="HS256")
        return {"access_token": new_access_token}

    # --- JWT 内部方法 ---
    def _create_token(
        self, user, expires_hours: int | None = None, expires_days: int | None = None
    ) -> str:
        """签发 JWT token，含 jti 用于登出黑名单。"""
        now = datetime.now(timezone.utc)
        if expires_hours is not None:
            exp = now + timedelta(hours=expires_hours)
        elif expires_days is not None:
            exp = now + timedelta(days=expires_days)
        else:
            exp = now + timedelta(hours=self.access_token_expire_hours)

        payload = {
            "jti": str(uuid.uuid4()),
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "nickname": user.nickname,
            "level": user.level,
            "blog_quality_level": user.blog_quality_level,
            "exp": exp,
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def _verify_token(self, token: str) -> dict:
        """验证并解析 JWT token。"""
        try:
            return jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthError("Token 已过期")  # noqa: B904
        except jwt.InvalidTokenError:
            raise AuthError("无效 Token")  # noqa: B904

    # --- 工具方法 ---
    def _user_to_dict(self, user) -> dict:
        """将 User 对象转为字典（用于返回）。"""
        return {
            "id": str(user.id),
            "nickname": user.nickname,
            "email": user.email,
            "username": user.username,
            "avatar": user.avatar,
            "bio": user.bio,
            "links": user.links,
            "badges": user.badges,
            "level": user.level,
            "blog_quality_level": user.blog_quality_level,
            "is_active": user.is_active,
            "deletion_status": user.deletion_status,
            "deletion_reason": user.deletion_reason,
            "deletion_expires_at": user.deletion_expires_at.isoformat()
            if user.deletion_expires_at
            else None,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            "login_count": user.login_count,
            "last_login_at": user.last_login_at.isoformat()
            if user.last_login_at
            else None,
            "last_login_ip": user.last_login_ip,
            "last_active_at": user.last_active_at.isoformat()
            if user.last_active_at
            else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    # --- 用户设置 ---
    async def get_user_settings(self, user_id: uuid.UUID) -> dict | None:
        """获取用户设置。"""
        from backend.plugins.auth.models import UserSettings

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()
            if not settings:
                return None
            return {
                "default_post_permission": settings.default_post_permission,
                "language": settings.language,
                "theme": settings.theme,
                "notify_comment_reply": settings.notify_comment_reply,
                "notify_like": settings.notify_like,
                "notify_system": settings.notify_system,
                "privacy_show_online": settings.privacy_show_online,
                "privacy_show_login_history": settings.privacy_show_login_history,
                "privacy_show_badges": settings.privacy_show_badges,
                "default_post_status": settings.default_post_status,
                "auto_save_interval": settings.auto_save_interval,
                "extras": settings.extras,
            }

    async def update_user_settings(self, user_id: uuid.UUID, updates: dict) -> dict:
        """更新用户设置（仅更新提供的字段）。"""
        from backend.plugins.auth.models import UserSettings

        allowed_fields = {
            "default_post_permission",
            "language",
            "theme",
            "notify_comment_reply",
            "notify_like",
            "notify_system",
            "privacy_show_online",
            "privacy_show_login_history",
            "privacy_show_badges",
            "default_post_status",
            "auto_save_interval",
            "extras",
        }

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()
            if not settings:
                raise AppError("设置不存在", code="settings_not_found", status_code=404)

            for key, value in updates.items():
                if key in allowed_fields:
                    setattr(settings, key, value)

            await session.commit()
            await session.refresh(settings)
            return await self.get_user_settings(user_id)  # type: ignore[return-value]

    # --- 登录历史 ---
    async def get_login_history(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> dict:
        """获取用户登录历史。"""
        from backend.plugins.auth.models import LoginHistory

        async with self.session_factory() as session:
            query = (
                select(LoginHistory)
                .where(LoginHistory.user_id == user_id)
                .order_by(LoginHistory.login_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(query)
            records = result.scalars().all()

            count_query = select(func.count(LoginHistory.id)).where(
                LoginHistory.user_id == user_id
            )
            total = (await session.execute(count_query)).scalar_one()

            return {
                "list": [
                    {
                        "id": r.id,
                        "ip": r.ip,
                        "device_name": r.device_name,
                        "location": r.location,
                        "login_at": r.login_at.isoformat() if r.login_at else None,
                    }
                    for r in records
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    # --- 违规记录 ---
    async def get_violations(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> dict:
        """获取用户违规记录。"""
        from backend.plugins.auth.models import ViolationRecord

        async with self.session_factory() as session:
            query = (
                select(ViolationRecord)
                .where(ViolationRecord.user_id == user_id)
                .order_by(ViolationRecord.banned_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(query)
            records = result.scalars().all()

            count_query = select(func.count(ViolationRecord.id)).where(
                ViolationRecord.user_id == user_id
            )
            total = (await session.execute(count_query)).scalar_one()

            return {
                "list": [
                    {
                        "id": r.id,
                        "violation_type": r.violation_type,
                        "reason": r.reason,
                        "ban_duration": r.ban_duration,
                        "banned_at": r.banned_at.isoformat() if r.banned_at else None,
                        "unbanned_at": r.unbanned_at.isoformat()
                        if r.unbanned_at
                        else None,
                    }
                    for r in records
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    # --- 已知设备 ---
    async def get_devices(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> dict:
        """获取用户已知设备列表。"""
        from backend.plugins.auth.models import KnownDevice

        async with self.session_factory() as session:
            query = (
                select(KnownDevice)
                .where(KnownDevice.user_id == user_id)
                .order_by(KnownDevice.last_seen_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(query)
            records = result.scalars().all()

            count_query = select(func.count(KnownDevice.id)).where(
                KnownDevice.user_id == user_id
            )
            total = (await session.execute(count_query)).scalar_one()

            return {
                "list": [
                    {
                        "id": r.id,
                        "device_name": r.device_name,
                        "device_mac": r.device_mac,
                        "first_seen_at": r.first_seen_at.isoformat()
                        if r.first_seen_at
                        else None,
                        "last_seen_at": r.last_seen_at.isoformat()
                        if r.last_seen_at
                        else None,
                    }
                    for r in records
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    # --- 用户管理（P0） ---
    async def list_users(
        self, page: int = 1, page_size: int = 20, status_filter: str | None = None
    ) -> dict:
        """分页查询用户列表，支持 active/disabled 过滤。"""
        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            query = select(User)
            if status_filter == "active":
                query = query.where(User.is_active.is_(True))
            elif status_filter == "disabled":
                query = query.where(User.is_active.is_(False))

            # 总数
            count_query = select(func.count(User.id))
            if status_filter == "active":
                count_query = count_query.where(User.is_active.is_(True))
            elif status_filter == "disabled":
                count_query = count_query.where(User.is_active.is_(False))
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()

            # 分页
            query = (
                query.order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(query)
            users = result.scalars().all()

            return {
                "list": [self._user_to_dict(u) for u in users],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def get_user(self, user_id: uuid.UUID) -> dict | None:
        """根据 ID 获取用户信息。"""
        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                return self._user_to_dict(user)
            return None

    async def update_user(
        self,
        user_id: uuid.UUID,
        level: int | None = None,
        is_active: bool | None = None,
        nickname: str | None = None,
        avatar: str | None = None,
        bio: str | None = None,
        links: list | None = None,
    ) -> dict:
        """修改用户信息。"""
        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise AppError("用户不存在", code="user_not_found", status_code=404)

            if level is not None:
                user.level = level
            if is_active is not None:
                user.is_active = is_active
            if nickname is not None:
                user.nickname = nickname
            if avatar is not None:
                user.avatar = avatar
            if bio is not None:
                user.bio = bio
            if links is not None:
                user.links = links

            await session.commit()
            await session.refresh(user)
            return self._user_to_dict(user)

    async def disable_user(self, user_id: uuid.UUID) -> dict:
        """禁用用户。"""
        return await self.update_user(user_id, is_active=False)

    async def enable_user(self, user_id: uuid.UUID) -> dict:
        """启用用户。"""
        return await self.update_user(user_id, is_active=True)

    async def soft_delete_user(
        self,
        user_id: uuid.UUID,
        reason: str,
        expires_in_days: int,
    ) -> dict:
        """软删除用户：标记删除状态、原因和过期时间，同时禁用账号。"""
        from datetime import datetime, timedelta, timezone

        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise AppError("用户不存在", code="user_not_found", status_code=404)

            if user.deleted_at is not None:
                raise AppError(
                    "该用户已被删除",
                    code="user_already_deleted",
                    status_code=409,
                )

            now = datetime.now(timezone.utc)
            user.is_active = False
            user.deletion_status = (
                "deleted_by_admin"
                if reason == "violation"
                else "user_requested_deletion"
            )
            user.deletion_reason = reason
            user.deletion_expires_at = now + timedelta(days=expires_in_days)
            user.deleted_at = now

            await session.commit()
            await session.refresh(user)
            return self._user_to_dict(user)

    # --- 管理员创建用户 ---
    async def admin_create_user(
        self, email: str, username: str, nickname: str, password: str, level: int = 5
    ) -> dict:
        """管理员手动创建用户（不自动赋予 P0）。"""
        from backend.plugins.auth.models import User, UserSettings

        if "@" not in email or not email.strip():
            raise AppError("邮箱格式不正确", code="invalid_email", status_code=400)
        email = email.strip().lower()

        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(func.lower(User.email) == email)
            )
            if result.scalar_one_or_none():
                raise AppError("邮箱已被使用", code="email_exists", status_code=409)

            result = await session.execute(
                select(User).where(User.username == username)
            )
            if result.scalar_one_or_none():
                raise AppError("用户名已存在", code="username_exists", status_code=409)

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            user_id = uuid.uuid4()
            user = User(
                id=user_id,
                email=email,
                username=username,
                nickname=nickname,
                password_hash=password_hash,
                level=level,
            )
            user.generate_sid("user")
            session.add(user)

            settings = UserSettings(user_id=user_id)
            session.add(settings)

            await session.commit()
            await session.refresh(user)
            return self._user_to_dict(user)

    async def reset_password(self, user_id: uuid.UUID, new_password: str) -> dict:
        """管理员重置用户密码（P0）。"""
        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise AppError("用户不存在", code="user_not_found", status_code=404)

            password_hash = bcrypt.hashpw(
                new_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            user.password_hash = password_hash

            await session.commit()
            await session.refresh(user)
            return self._user_to_dict(user)

    # ── 用户统计 ──

    async def get_user_stats(self) -> dict:
        """获取用户相关统计（用于用户管理 Dashboard）。"""
        from datetime import datetime, timezone

        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            # 总用户数
            total_result = await session.execute(select(func.count(User.id)))
            total_users = total_result.scalar_one()

            # 活跃用户数
            active_result = await session.execute(
                select(func.count(User.id)).where(User.is_active.is_(True))
            )
            active_users = active_result.scalar_one()

            # 禁用用户数
            disabled_result = await session.execute(
                select(func.count(User.id)).where(User.is_active.is_(False))
            )
            disabled_users = disabled_result.scalar_one()

            # 今日新增
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_result = await session.execute(
                select(func.count(User.id)).where(User.created_at >= today_start)
            )
            today_new = today_result.scalar_one()

            # 各等级用户数
            level_query = (
                select(User.level, func.count(User.id).label("count"))
                .group_by(User.level)
                .order_by(User.level)
            )
            level_result = await session.execute(level_query)
            by_level = {row.level: row.count for row in level_result.all()}

            # 每日新增趋势（最近 30 天）
            from datetime import timedelta

            start_date = today_start - timedelta(days=29)

            daily_query = (
                select(
                    func.date(User.created_at).label("date"),
                    func.count().label("count"),
                )
                .where(User.created_at >= start_date)
                .group_by(func.date(User.created_at))
                .order_by(func.date(User.created_at))
            )
            daily_result = await session.execute(daily_query)
            daily_map = {row.date: row.count for row in daily_result.all()}

            trend = []
            for i in range(30):
                date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                trend.append({"date": date, "count": int(daily_map.get(date, 0))})

        return {
            "total_users": total_users,
            "active_users": active_users,
            "disabled_users": disabled_users,
            "today_new": today_new,
            "by_level": by_level,
            "daily_trend": trend,
        }

    # ── 页面组件权限管理 ──

    async def get_page_permissions(self, level: int) -> dict[str, dict[str, bool]]:
        """获取指定 level 的页面组件权限映射。

        返回格式：{ page_name: { component_name: visible } }
        """
        from backend.plugins.auth.models import PageComponentPermission

        async with self.session_factory() as session:
            result = await session.execute(
                select(PageComponentPermission).where(
                    PageComponentPermission.level == level
                )
            )
            rows = result.scalars().all()

        mapping: dict[str, dict[str, bool]] = {}
        for row in rows:
            if row.page_name not in mapping:
                mapping[row.page_name] = {}
            mapping[row.page_name][row.component_name] = row.visible
        return mapping

    async def get_all_permission_levels(self) -> list[int]:
        """获取所有已配置权限数据的 level 列表。"""
        from backend.plugins.auth.models import PageComponentPermission

        async with self.session_factory() as session:
            result = await session.execute(
                select(PageComponentPermission.level)
                .distinct()
                .order_by(PageComponentPermission.level)
            )
            return [row[0] for row in result.all()]

    async def set_page_component(
        self, level: int, page_name: str, component_name: str, visible: bool
    ) -> None:
        """设置单个页面组件的可见性。不存在则插入，存在则更新。"""
        from backend.plugins.auth.models import PageComponentPermission

        async with self.session_factory() as session:
            result = await session.execute(
                select(PageComponentPermission).where(
                    PageComponentPermission.level == level,
                    PageComponentPermission.page_name == page_name,
                    PageComponentPermission.component_name == component_name,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                row.visible = visible
            else:
                row = PageComponentPermission(
                    level=level,
                    page_name=page_name,
                    component_name=component_name,
                    visible=visible,
                )
                session.add(row)
            await session.commit()

    async def set_page_defaults(
        self, level: int, page_name: str, visible_default: bool
    ) -> None:
        """批量设置指定页面下所有组件的可见性。"""
        from backend.plugins.auth.models import PageComponentPermission

        async with self.session_factory() as session:
            result = await session.execute(
                select(PageComponentPermission).where(
                    PageComponentPermission.level == level,
                    PageComponentPermission.page_name == page_name,
                )
            )
            rows = result.scalars().all()
            for row in rows:
                row.visible = visible_default
            await session.commit()
