# ============================================================
# 用户数据结构（纯展示用，无实际运行作用）
# ============================================================

user_data = {
    "UID_001": {
        # ========== 基本信息 ==========
        "user_id": "",  # 用户ID
        "nickname": "",  # 昵称
        "previous_names": [],  # 曾用名列表（改名时记录历史名称）
        "email": "",  # 邮箱
        "password_hash": "",  # 密码哈希
        "password_salt": "",  # 密码哈希盐值
        "avatar": "",  # 用户头像URL
        "links": [],  # 个人链接列表（个人网站、社交链接等）
        "bio": "",  # 个人简介（可选补充）
        "status": "",  # 账号状态: active / banned / deactivated
        "badges": [],  # 已获得徽章ID列表（关联徽章系统）
        # ========== 权限 ==========
        "permission_level": "",  # 权限等级
        # ========== 用户设置 / 偏好 ==========
        "settings": {
            "default_post_permission": "",  # 发帖默认权限等级
            "language": "",  # 界面语言偏好
            "theme": "",  # 界面主题: light / dark / auto
            "notifications": {
                "comment_reply": True,  # 评论回复通知
                "like": True,  # 点赞通知
                "system_announcement": True,  # 系统公告通知
            },
            "privacy": {
                "show_online_status": True,  # 是否展示在线状态
                "show_login_history": False,  # 是否公开登录历史
                "show_badges": True,  # 是否展示徽章
            },
            "content": {
                "default_post_status": "",  # 发帖默认状态: draft / published
                "auto_save_interval": 0,  # 自动保存间隔（秒）
            },
        },
        # ========== 资产（KV 结构） ==========
        "assets": {
            "AST_001": {
                "asset_id": "AST_001",  # 资产ID
                "asset_type": "",  # 资产类型（如: image / video / file）
                "storage": "",  # 存储位置: oss / database / local
            },
        },
        # ========== 审计 ==========
        "token_ids": [],  # 关联的TOKEN ID列表（实际内容存 token 表）
        "registered_at": "",  # 注册时间
        "login_count": 0,  # 累计登录次数
        "last_login_at": "",  # 最近登录时间
        "last_login_ip": "",  # 最近登录IP
        "last_active_at": "",  # 最后活跃时间
        "known_devices": [  # 已知设备列表
            {
                "device_name": "",  # 设备名称
                "device_mac": "",  # 设备MAC地址
                "first_seen_at": "",  # 首次出现时间
                "last_seen_at": "",  # 最后出现时间
            },
        ],
        "login_history": [  # 登录历史记录
            {
                "login_at": "",  # 登录时间
                "ip": "",  # 登录IP
                "device_mac": "",  # 登录设备MAC
                "location": "",  # 登录地点（可选）
            },
        ],
        # ========== 违规记录（KV 结构） ==========
        "violations": {
            "VIO_001": {
                "violation_id": "VIO_001",  # 违规记录ID
                "violation_type": "",  # 违规类型
                "reason": "",  # 违规原因说明
                "ban_duration": 0,  # 封禁时长（小时），0表示永久封禁
                "banned_at": "",  # 封禁时间
                "unbanned_at": "",  # 解封时间（空表示未解封）
            },
        },
    },
}
