# ============================================================
# 评论数据结构（纯展示用，无实际运行作用）
# ============================================================

comment_data = {
    # 评论 ID 作为 key
    "CID_001": {
        "comment_id": "CID_001",  # 评论ID
        "parent_id": "",  # 父评论ID（空表示顶级评论）
        "user_id": "",  # 发表用户ID（仅记录ID，名称/头像等联查即可）
        "content": "",  # 评论内容
        "like_count": 0,  # 点赞数
        "reply_ids": [],  # 回复此评论的所有评论ID列表
        "status": "",  # 状态: visible / hidden / deleted
        "created_at": "",  # 创建时间
        "updated_at": "",  # 更新时间
    },
    "CID_002": {
        "comment_id": "CID_002",
        "parent_id": "CID_001",  # 回复 CID_001
        "user_id": "",
        "content": "",
        "like_count": 0,
        "reply_ids": [],
        "status": "",
        "created_at": "",
        "updated_at": "",
    },
}
