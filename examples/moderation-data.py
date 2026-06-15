# ============================================================
# 审核数据结构（纯展示用，无实际运行作用）
# ============================================================

moderation_records = {
    "MOD_001": {
        "moderation_id": "MOD_001",  # 审核记录ID
        "target_type": "",  # 审核对象类型: post / comment / user
        "target_id": "",  # 审核对象ID
        "submitter_id": "",  # 提交审核的用户ID
        "reviewer_id": "",  # 审核人ID（空表示未分配）
        "status": "",  # 审核状态: pending / approved / rejected
        "reason": "",  # 驳回原因（驳回时填写）
        "submitted_at": "",  # 提交审核时间
        "reviewed_at": "",  # 审核完成时间
    },
}


# ============================================================
# 变更记录数据结构（记录每次内容改动前后的对比）
# ============================================================

change_logs = {
    "CHG_001": {
        "change_id": "CHG_001",  # 变更记录ID
        "target_type": "",  # 变更对象类型: post / comment / user
        "target_id": "",  # 变更对象ID
        "operator_id": "",  # 操作人ID
        "operation": "",  # 操作类型: create / update / delete / submit_for_review
        "changes": {  # 变更内容（字段级别的改前/改后）
            "field_name": {
                "old": "",
                "new": "",
            },
        },
        "created_at": "",  # 变更时间
    },
}
