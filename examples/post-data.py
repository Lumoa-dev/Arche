# ============================================================
# 帖子完整数据结构（纯展示用，无实际运行作用）
#
# 存储方式：两个表
#   blog_posts      — 帖子主表（含 metadata + introduction JSON）
#   blog_paragraphs — 段落独立表（每段一行）
# 顺序控制：blog_posts.paragraph_ids（JSON 数组）决定段落顺序
# 段落实体：段落表每行一个段落，不关心顺序
# 评论关联：blog_comments.paragraph_pid → blog_paragraphs.pid
# ============================================================

post_data = {
    # ========== 原信息区域 ==========
    "metadata": {
        "post_id": "",  # 帖子唯一标识
        "user_id": "",  # 作者用户ID
        "title": "",  # 帖子标题
        "slug": "",  # URL 友好标识
        "status": "",  # 帖子状态: draft / published / archived
        "cover_url": "",  # 封面图片地址
        "tags": [],  # 标签列表
        "category_id": "",  # 所属分类ID
        "view_count": 0,  # 浏览量
        "like_count": 0,  # 点赞数
        "comment_count": 0,  # 评论数
        "is_pinned": False,  # 是否置顶
        "is_featured": False,  # 是否精选
        "permission_level": "",  # 权限等级: public / members_only / admin_only
        "created_at": "",  # 创建时间
        "updated_at": "",  # 更新时间
        "published_at": "",  # 发布时间
    },
    # ========== 引言信息区域 ==========
    "introduction": {
        "abstract": "",  # 摘要 / 内容简介
        "background": "",  # 背景说明
        "purpose": "",  # 写作目的 / 动机
        "key_points": [],  # 关键要点列表
        "reading_time": 0,  # 预计阅读时间（分钟）
        "difficulty_level": "",  # 难度等级: beginner / intermediate / advanced
    },
    # ========== 段落顺序（JSON 数组，控制渲染顺序） ==========
    # 段落顺序由帖子控制，不在段落实体中存 order 字段
    "paragraph_ids": ["PID_001", "PID_002"],
    # ========== 段落信息区域（KV 结构） ==========
    # key = 段落ID（全局唯一: post_id 前8位_序号），value = 段落内容
    # 评论通过 blog_comments.paragraph_pid 关联，段落中不存评论ID
    "paragraphs": {
        "PID_001": {  # 段落ID = 帖子ID前8位 + 三位序号
            "content": "",  # 段落正文内容
            "type": "",  # 段落类型: text / image / code / quote / heading
            "word_count": 0,  # 段落字数
            "heading": "",  # 段落小标题（可选）
            "media_url": "",  # 媒体资源链接（图片/视频段落使用）
            "caption": "",  # 媒体说明文字（可选）
        },
        "PID_002": {  # 第二个段落
            "content": "",
            "type": "",
            "word_count": 0,
            "heading": "",
            "media_url": "",
            "caption": "",
        },
    },
}
