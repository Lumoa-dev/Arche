export interface paths {
  '/api/auth/register': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Register
     * @description 用户注册，默认 P5 等级。
     */
    post: operations['register_api_auth_register_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/login': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Login
     * @description 用户登录，返回 JWT token。
     */
    post: operations['login_api_auth_login_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/logout': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Logout
     * @description 用户登出。
     */
    post: operations['logout_api_auth_logout_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/me': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Me
     * @description 获取当前登录用户信息。
     */
    get: operations['get_me_api_auth_me_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/refresh': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Refresh
     * @description 刷新 access token。
     */
    post: operations['refresh_api_auth_refresh_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/users': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Users
     * @description 用户列表（P0）。
     */
    get: operations['list_users_api_auth_users_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/users/{user_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get User
     * @description 用户详情（P0）。
     */
    get: operations['get_user_api_auth_users__user_id__get']
    /**
     * Update User
     * @description 修改用户等级/状态（P0）。
     */
    put: operations['update_user_api_auth_users__user_id__put']
    post?: never
    /**
     * Delete User
     * @description 禁用用户（P0）。
     */
    delete: operations['delete_user_api_auth_users__user_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/users/{user_id}/disable': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Disable User
     * @description 禁用用户（P0）。不能禁用自己。
     */
    post: operations['disable_user_api_auth_users__user_id__disable_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/users/{user_id}/enable': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Enable User
     * @description 启用用户（P0）。
     */
    post: operations['enable_user_api_auth_users__user_id__enable_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/auth/admin/users': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Admin Create User
     * @description 管理员手动创建用户（P0）。
     */
    post: operations['admin_create_user_api_auth_admin_users_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/deploy': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Trigger Deploy */
    post: operations['trigger_deploy_api_deploy_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/monitor/templates': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Templates
     * @description 获取当前用户的监控模板列表。
     */
    get: operations['list_templates_api_monitor_templates_get']
    put?: never
    /**
     * Create Template
     * @description 创建新的监控模板。
     */
    post: operations['create_template_api_monitor_templates_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/monitor/templates/{template_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Template
     * @description 获取单个监控模板。
     */
    get: operations['get_template_api_monitor_templates__template_id__get']
    /**
     * Update Template
     * @description 更新监控模板。
     */
    put: operations['update_template_api_monitor_templates__template_id__put']
    post?: never
    /**
     * Delete Template
     * @description 删除监控模板。
     */
    delete: operations['delete_template_api_monitor_templates__template_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/monitor/components/{component_id}/data': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Component Data
     * @description 获取组件数据。
     */
    get: operations['get_component_data_api_monitor_components__component_id__data_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Posts
     * @description 帖子列表（公开，支持搜索和标签筛选，按权限过滤）。
     */
    get: operations['get_posts_api_blog_posts_get']
    put?: never
    /**
     * Create Post
     * @description 发帖（需登录，进入审核队列）。
     */
    post: operations['create_post_api_blog_posts_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/by-id/{post_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Post By Id
     * @description 按 ID 获取帖子详情（含标签，按权限过滤）。
     */
    get: operations['get_post_by_id_api_blog_posts_by_id__post_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/{slug}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Post
     * @description 帖子详情（按权限过滤）。
     */
    get: operations['get_post_api_blog_posts__slug__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/my-posts': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get My Posts
     * @description 我的帖子列表（需登录，包含所有状态）。
     */
    get: operations['get_my_posts_api_blog_my_posts_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/{post_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    /**
     * Update Post
     * @description 编辑帖子（作者本人）。
     */
    put: operations['update_post_api_blog_posts__post_id__put']
    post?: never
    /**
     * Delete Post
     * @description 删除帖子（作者本人 或 P0）。
     */
    delete: operations['delete_post_api_blog_posts__post_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/{post_id}/comments': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Comments
     * @description 评论列表（公开）。
     */
    get: operations['get_comments_api_blog_posts__post_id__comments_get']
    put?: never
    /**
     * Create Comment
     * @description 评论（需登录）。
     */
    post: operations['create_comment_api_blog_posts__post_id__comments_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/{post_id}/like': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Toggle Like
     * @description 点赞（需登录，幂等）。
     */
    post: operations['toggle_like_api_blog_posts__post_id__like_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/moderation/pending': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Pending Posts
     * @description 待审核列表（P0）。
     */
    get: operations['get_pending_posts_api_blog_moderation_pending_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/moderation/{post_id}/approve': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Approve Post
     * @description 通过审核（P0）。
     */
    post: operations['approve_post_api_blog_moderation__post_id__approve_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/moderation/{post_id}/reject': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Reject Post
     * @description 拒绝审核（P0）。
     */
    post: operations['reject_post_api_blog_moderation__post_id__reject_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/moderation/batch-approve': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Batch Approve Posts
     * @description 批量通过审核（P0）。
     */
    post: operations['batch_approve_posts_api_blog_moderation_batch_approve_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/moderation/batch-reject': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Batch Reject Posts
     * @description 批量拒绝审核（P0）。
     */
    post: operations['batch_reject_posts_api_blog_moderation_batch_reject_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/favorites/{post_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Add Favorite
     * @description 收藏帖子（需登录）。
     */
    post: operations['add_favorite_api_blog_favorites__post_id__post']
    /**
     * Remove Favorite
     * @description 取消收藏（需登录）。
     */
    delete: operations['remove_favorite_api_blog_favorites__post_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/favorites': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Favorites
     * @description 我的收藏列表（需登录）。
     */
    get: operations['get_favorites_api_blog_favorites_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/{post_id}/favorite-status': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Favorite Status
     * @description 检查收藏状态（需登录）。
     */
    get: operations['get_favorite_status_api_blog_posts__post_id__favorite_status_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/reports': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Create Report
     * @description 举报（需登录）。
     */
    post: operations['create_report_api_blog_reports_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/import': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Import Post
     * @description 从文件导入帖子（需登录）。
     */
    post: operations['import_post_api_blog_import_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/tags': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Tags
     * @description 标签列表（公开）。
     */
    get: operations['get_tags_api_blog_tags_get']
    put?: never
    /**
     * Create Tag
     * @description 创建标签（需登录）。
     */
    post: operations['create_tag_api_blog_tags_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/by-tag/{tag_name}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Posts By Tag
     * @description 按标签查询帖子（按权限过滤）。
     */
    get: operations['get_posts_by_tag_api_blog_posts_by_tag__tag_name__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/{post_id}/tags': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Post Tags
     * @description 获取帖子标签（公开）。
     */
    get: operations['get_post_tags_api_blog_posts__post_id__tags_get']
    put?: never
    /**
     * Add Tag To Post
     * @description 给帖子加标签（作者本人）。
     */
    post: operations['add_tag_to_post_api_blog_posts__post_id__tags_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/blog/posts/{post_id}/tags/{tag_name}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    post?: never
    /**
     * Remove Tag From Post
     * @description 从帖子移除标签（作者本人）。
     */
    delete: operations['remove_tag_from_post_api_blog_posts__post_id__tags__tag_name__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/stats': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Stats
     * @description 云工作台统计数据（P0）。
     */
    get: operations['get_stats_api_cloud_stats_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Jobs
     * @description 训练任务列表（P0）。
     */
    get: operations['list_jobs_api_cloud_jobs_get']
    put?: never
    /**
     * Create Job
     * @description 创建训练任务（P0）。
     */
    post: operations['create_job_api_cloud_jobs_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Job
     * @description 训练任务详情（P0）。
     */
    get: operations['get_job_api_cloud_jobs__job_id__get']
    put?: never
    post?: never
    /**
     * Delete Job
     * @description 删除训练任务（P0）。
     */
    delete: operations['delete_job_api_cloud_jobs__job_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/start': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Start Job
     * @description 启动训练任务（P0）。
     */
    post: operations['start_job_api_cloud_jobs__job_id__start_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/stop': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Stop Job
     * @description 停止训练任务（P0）。
     */
    post: operations['stop_job_api_cloud_jobs__job_id__stop_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/complete': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Complete Job
     * @description 标记任务完成（P0）。
     */
    post: operations['complete_job_api_cloud_jobs__job_id__complete_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/fail': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Fail Job
     * @description 标记任务失败（P0）。
     */
    post: operations['fail_job_api_cloud_jobs__job_id__fail_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/logs': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Job Logs
     * @description 获取训练日志（P0）。
     */
    get: operations['get_job_logs_api_cloud_jobs__job_id__logs_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/instances': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Instances
     * @description 训练实例列表（P0）。
     */
    get: operations['list_instances_api_cloud_jobs__job_id__instances_get']
    put?: never
    /**
     * Create Instance
     * @description 创建训练实例（P0）。
     */
    post: operations['create_instance_api_cloud_jobs__job_id__instances_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/instances/{instance_id}/start': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Start Instance
     * @description 启动训练实例（P0）。
     */
    post: operations['start_instance_api_cloud_instances__instance_id__start_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/instances/{instance_id}/stop': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Stop Instance
     * @description 停止训练实例（P0）。
     */
    post: operations['stop_instance_api_cloud_instances__instance_id__stop_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/costs': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Costs
     * @description 训练费用汇总（P0）。
     */
    get: operations['get_costs_api_cloud_costs_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/instances/{instance_id}/gpu-metrics': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Gpu Metrics
     * @description GPU 实时指标（P0）。
     */
    get: operations['get_gpu_metrics_api_cloud_instances__instance_id__gpu_metrics_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/launch': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Launch Job
     * @description 一键启动全链路（P1）。
     */
    post: operations['launch_job_api_cloud_jobs__job_id__launch_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/progress': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Job Progress
     * @description 查询实时训练进度（P1）。
     */
    get: operations['get_job_progress_api_cloud_jobs__job_id__progress_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/jobs/{job_id}/steps': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Job Steps
     * @description 查询步骤执行历史（P1）。
     */
    get: operations['get_job_steps_api_cloud_jobs__job_id__steps_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/datasets': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Datasets
     * @description 数据集列表（P0）。
     */
    get: operations['list_datasets_api_cloud_datasets_get']
    put?: never
    /**
     * Create Dataset
     * @description 创建/导入数据集（P0）。
     */
    post: operations['create_dataset_api_cloud_datasets_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/datasets/{dataset_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Dataset
     * @description 数据集详情（P0）。
     */
    get: operations['get_dataset_api_cloud_datasets__dataset_id__get']
    put?: never
    post?: never
    /**
     * Delete Dataset
     * @description 删除数据集（P0）。
     */
    delete: operations['delete_dataset_api_cloud_datasets__dataset_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/datasets/{dataset_id}/sync': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Sync Dataset
     * @description 同步数据集到阿里云（P0）。
     */
    post: operations['sync_dataset_api_cloud_datasets__dataset_id__sync_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/repos': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Repos
     * @description 代码仓库列表（P0）。
     */
    get: operations['list_repos_api_cloud_repos_get']
    put?: never
    /**
     * Create Repo
     * @description 添加代码仓库（P0）。
     */
    post: operations['create_repo_api_cloud_repos_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/repos/{repo_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    post?: never
    /**
     * Delete Repo
     * @description 删除代码仓库（P0）。
     */
    delete: operations['delete_repo_api_cloud_repos__repo_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/repos/{repo_id}/sync': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Sync Repo
     * @description 同步代码仓库最新版本（P0）。
     */
    post: operations['sync_repo_api_cloud_repos__repo_id__sync_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/artifacts': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Artifacts
     * @description 制品列表（P0）。
     */
    get: operations['list_artifacts_api_cloud_artifacts_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/artifacts/{artifact_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Artifact
     * @description 制品详情（P0）。
     */
    get: operations['get_artifact_api_cloud_artifacts__artifact_id__get']
    put?: never
    post?: never
    /**
     * Delete Artifact
     * @description 删除制品（P0）。
     */
    delete: operations['delete_artifact_api_cloud_artifacts__artifact_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/cloud/artifacts/{artifact_id}/download': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Download Artifact
     * @description 下载制品（P0）。
     */
    get: operations['download_artifact_api_cloud_artifacts__artifact_id__download_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/admin/config': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Configs
     * @description 列出所有配置（可按 group 过滤），敏感字段掩码返回。
     */
    get: operations['list_configs_api_admin_config_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/admin/config/{key}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Config
     * @description 获取单条配置详情（敏感字段也返回真实值）。
     */
    get: operations['get_config_api_admin_config__key__get']
    /**
     * Update Config
     * @description 更新配置值，同时清除内存缓存。
     */
    put: operations['update_config_api_admin_config__key__put']
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/admin/config/groups': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Groups
     * @description 列出所有配置分组。
     */
    get: operations['list_groups_api_admin_config_groups_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/admin/config/reload': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Reload Config
     * @description 强制清除所有配置缓存，下次请求时重新从数据库加载。
     */
    post: operations['reload_config_api_admin_config_reload_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/github/health/status': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Health Status
     * @description 检查 GitHub 代理健康状态，检测 CLI 和 HTTP 模式是否可用。
     */
    get: operations['get_health_status_api_github_health_status_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/github/raw/{path}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Proxy Raw
     * @description 代理 GitHub 静态资源（需 P1 权限）。
     *
     *     转发到 https://raw.githubusercontent.com/{path}，
     *     适用于 raw 文件内容（图片、文本等）。
     *
     *     Args:
     *         mode: 模式选择 - auto（默认）, http, cli
     */
    get: operations['proxy_raw_api_github_raw__path__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/github/cache/clear': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Clear Cache
     * @description 清空代理缓存（需 P1 权限）。
     */
    post: operations['clear_cache_api_github_cache_clear_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/github/{path}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Proxy Github Get
     * @description 反向代理 GitHub API - GET（需 P1 权限）。
     */
    get: operations['proxy_github_get_api_github__path__get']
    /**
     * Proxy Github Put
     * @description 反向代理 GitHub API - PUT（需 P1 权限）。
     */
    put: operations['proxy_github_put_api_github__path__put']
    /**
     * Proxy Github Post
     * @description 反向代理 GitHub API - POST（需 P1 权限）。
     */
    post: operations['proxy_github_post_api_github__path__post']
    /**
     * Proxy Github Delete
     * @description 反向代理 GitHub API - DELETE（需 P1 权限）。
     */
    delete: operations['proxy_github_delete_api_github__path__delete']
    options?: never
    head?: never
    /**
     * Proxy Github Patch
     * @description 反向代理 GitHub API - PATCH（需 P1 权限）。
     */
    patch: operations['proxy_github_patch_api_github__path__patch']
    trace?: never
  }
  '/api/oss/upload': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Upload File
     * @description 用户上传文件（流式写入 + 限速）。
     */
    post: operations['upload_file_api_oss_upload_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/files/{file_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Download File
     * @description 下载文件（流式返回）。
     */
    get: operations['download_file_api_oss_files__file_id__get']
    put?: never
    post?: never
    /**
     * Delete File
     * @description 删除文件。
     */
    delete: operations['delete_file_api_oss_files__file_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/my': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List My Files
     * @description 我的文件列表。
     */
    get: operations['list_my_files_api_oss_my_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/external/{tenant_id}/upload': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * External Upload
     * @description 外部租户写入文件。
     */
    post: operations['external_upload_api_oss_external__tenant_id__upload_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/external/{tenant_id}/files': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List External Files
     * @description 外部租户文件列表。
     */
    get: operations['list_external_files_api_oss_external__tenant_id__files_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/storage/stats': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Storage Stats
     * @description 存储统计。默认全局统计，user_scope=true 时仅统计当前用户。
     */
    get: operations['get_storage_stats_api_oss_storage_stats_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/quota': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Quota
     * @description 用户存储配额使用情况。
     */
    get: operations['get_quota_api_oss_quota_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/evict': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Trigger Eviction
     * @description 手动触发冷热迁移（P0）。
     */
    post: operations['trigger_eviction_api_oss_admin_evict_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/quotas': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List User Quotas
     * @description 用户配额列表（P0）。
     */
    get: operations['list_user_quotas_api_oss_admin_quotas_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/quotas/{user_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    /**
     * Update User Quota
     * @description 更新用户配额和限速倍率（P0）。
     */
    put: operations['update_user_quota_api_oss_admin_quotas__user_id__put']
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/rate-limit': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Rate Limit Config
     * @description 获取全局限速配置（P0）。
     */
    get: operations['get_rate_limit_config_api_oss_admin_rate_limit_get']
    /**
     * Update Global Rate Limit
     * @description 更新全局限速（P0）。
     */
    put: operations['update_global_rate_limit_api_oss_admin_rate_limit_put']
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/rate-limit/users/{user_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    /**
     * Update User Speed Multiplier
     * @description 更新用户限速倍率（P0）。
     */
    put: operations['update_user_speed_multiplier_api_oss_admin_rate_limit_users__user_id__put']
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/files': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Admin List Files
     * @description 管理员文件列表，可按用户过滤（P0）。
     */
    get: operations['admin_list_files_api_oss_admin_files_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/files/{file_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    post?: never
    /**
     * Admin Delete File
     * @description 管理员删除任意文件（P0）。
     */
    delete: operations['admin_delete_file_api_oss_admin_files__file_id__delete']
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/stats': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Admin Stats
     * @description OSS 统计大盘（P0）。
     */
    get: operations['admin_stats_api_oss_admin_stats_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/oss/admin/stats/top-users': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Top Users By Storage
     * @description 按存储使用量排行的用户列表（P0）。
     */
    get: operations['top_users_by_storage_api_oss_admin_stats_top_users_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/system/summary': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Summary
     * @description 系统概览（P0）。
     */
    get: operations['get_summary_api_system_summary_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/system/cpu': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Cpu
     * @description CPU 详情（P0）。
     */
    get: operations['get_cpu_api_system_cpu_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/system/memory': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Memory
     * @description 内存详情（P0）。
     */
    get: operations['get_memory_api_system_memory_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/system/disk': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Disk
     * @description 磁盘详情（P0）。
     */
    get: operations['get_disk_api_system_disk_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/system/network': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Network
     * @description 网络 I/O（P0）。
     */
    get: operations['get_network_api_system_network_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/system/history': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get History
     * @description 历史数据（P0）。
     */
    get: operations['get_history_api_system_history_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/system/processes': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Processes
     * @description 进程列表（P0）。
     */
    get: operations['get_processes_api_system_processes_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/status': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Status
     * @description 获取爬虫运行状态。
     */
    get: operations['get_status_api_crawler_status_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/start': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Start Crawler
     * @description 启动爬虫。
     */
    post: operations['start_crawler_api_crawler_start_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/stop': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /**
     * Stop Crawler
     * @description 停止爬虫。
     */
    post: operations['stop_crawler_api_crawler_stop_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/records': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Records
     * @description 分页抓取记录。
     */
    get: operations['list_records_api_crawler_records_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/records/{record_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Record
     * @description 单条记录详情。
     */
    get: operations['get_record_api_crawler_records__record_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/records/{record_id}/file': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Record File
     * @description 下载 OSS 中对应文件内容。
     */
    get: operations['get_record_file_api_crawler_records__record_id__file_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/seeds': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Seeds
     * @description 种子池状态。
     */
    get: operations['get_seeds_api_crawler_seeds_get']
    put?: never
    /**
     * Add Seed
     * @description 手动添加种子 URL。
     */
    post: operations['add_seed_api_crawler_seeds_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/blacklist': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Blacklist
     * @description 黑名单列表。
     */
    get: operations['get_blacklist_api_crawler_blacklist_get']
    put?: never
    /**
     * Add Blacklist
     * @description 添加黑名单规则。
     */
    post: operations['add_blacklist_api_crawler_blacklist_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/crawler/stats': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Stats
     * @description 统计信息。
     */
    get: operations['get_stats_api_crawler_stats_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/assets': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * List Assets
     * @description 统一资产目录（P0）。
     */
    get: operations['list_assets_api_assets_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/assets/search': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Search Assets
     * @description 资产搜索（P0）。
     */
    get: operations['search_assets_api_assets_search_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/assets/stats': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /**
     * Get Asset Stats
     * @description 资产统计（P0）。
     */
    get: operations['get_asset_stats_api_assets_stats_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
}
export type webhooks = Record<string, never>
export interface components {
  schemas: {
    /** AddBlacklistRequest */
    AddBlacklistRequest: {
      /** Pattern */
      pattern: string
      /**
       * Reason
       * @default
       */
      reason: string
    }
    /** AddSeedRequest */
    AddSeedRequest: {
      /** Url */
      url: string
    }
    /** BatchModerationRequest */
    BatchModerationRequest: {
      /**
       * Post Ids
       * @description 帖子 ID 列表
       */
      post_ids: string[]
    }
    /** Body_external_upload_api_oss_external__tenant_id__upload_post */
    Body_external_upload_api_oss_external__tenant_id__upload_post: {
      /** File */
      file: string
    }
    /** Body_import_post_api_blog_import_post */
    Body_import_post_api_blog_import_post: {
      /** File */
      file: string
      /**
       * Required Level
       * @default 5
       */
      required_level: number
      /**
       * Tags
       * @default
       */
      tags: string
    }
    /** Body_upload_file_api_oss_upload_post */
    Body_upload_file_api_oss_upload_post: {
      /** File */
      file: string
      /**
       * Is Private
       * @default false
       */
      is_private: boolean
    }
    /** CreateCodeRepoRequest */
    CreateCodeRepoRequest: {
      /**
       * Name
       * @description 仓库名称
       */
      name: string
      /**
       * Git Url
       * @description Git仓库URL
       */
      git_url: string
      /**
       * Git Branch
       * @description 分支名
       * @default main
       */
      git_branch: string
      /**
       * Git Token
       * @description Git认证token（加密存储）
       */
      git_token?: string | null
    }
    /** CreateCommentRequest */
    CreateCommentRequest: {
      /**
       * Content
       * @description 评论内容
       */
      content: string
      /**
       * Parent Id
       * @description 父评论 ID（回复）
       */
      parent_id?: string | null
    }
    /** CreateDatasetRequest */
    CreateDatasetRequest: {
      /**
       * Name
       * @description 数据集名称
       */
      name: string
      /**
       * Description
       * @description 数据集描述
       */
      description?: string | null
      /**
       * Path
       * @description 虚拟路径，如 datasets/my_data/v1
       */
      path: string
      /**
       * Source
       * @description 数据来源：local/modelscope/aliyun
       * @default local
       */
      source: string
      /**
       * Tags
       * @description 标签列表
       * @default []
       */
      tags: string[] | null
      /**
       * Config
       * @description 扩展配置（如modelscope ID、token等）
       * @default {}
       */
      config: {
        [key: string]: unknown
      } | null
    }
    /** CreateInstanceRequest */
    CreateInstanceRequest: {
      /**
       * Instance Name
       * @description 实例名称
       */
      instance_name: string
      /**
       * Gpu Type
       * @description GPU 类型
       */
      gpu_type: string
      /**
       * Provider
       * @description Provider 名称
       * @default mock
       */
      provider: string
    }
    /** CreateJobRequest */
    CreateJobRequest: {
      /**
       * Name
       * @description 任务名称
       */
      name: string
      /**
       * Config
       * @description 模型配置（JSON）
       */
      config: {
        [key: string]: unknown
      }
      /**
       * Repo Url
       * @description Git 仓库 URL（必填）
       */
      repo_url: string
      /**
       * Repo Branch
       * @description 分支名
       * @default main
       */
      repo_branch: string
      /**
       * Repo Token
       * @description Git 认证 token
       */
      repo_token?: string | null
      /**
       * Dataset Config
       * @description 数据集配置
       * @default {}
       */
      dataset_config: {
        [key: string]: unknown
      }
      /**
       * Training Script
       * @description 训练脚本路径
       * @default train.py
       */
      training_script: string
      /**
       * Requirements File
       * @description 依赖文件路径
       * @default requirements.txt
       */
      requirements_file: string
      /**
       * Log Pattern
       * @description 日志解析正则
       */
      log_pattern?: string | null
      /**
       * Provider
       * @description Provider 名称
       * @default mock
       */
      provider: string
      /**
       * Gpu Type
       * @description GPU 类型
       * @default RTX4090
       */
      gpu_type: string
      /**
       * Instance Name
       * @description 实例名称
       */
      instance_name?: string | null
    }
    /** CreatePostRequest */
    CreatePostRequest: {
      /**
       * Title
       * @description 标题
       */
      title: string
      /**
       * Content
       * @description 正文内容
       */
      content: string
      /**
       * Tags
       * @description 标签列表
       */
      tags?: string[]
      /**
       * Required Level
       * @description 阅读所需最低 P 等级（0-5，数字越小权限越高）
       * @default 5
       */
      required_level: number
    }
    /** CreateReportRequest */
    CreateReportRequest: {
      /**
       * Post Id
       * @description 被举报帖子 ID
       */
      post_id: string
      /**
       * Reason
       * @description 举报原因
       */
      reason?: string | null
    }
    /** CreateUserRequest */
    CreateUserRequest: {
      /**
       * Email
       * @description 邮箱
       */
      email: string
      /**
       * Username
       * @description 用户名
       */
      username: string
      /**
       * Password
       * @description 密码
       */
      password: string
      /**
       * Level
       * @description 用户等级（默认 5）
       */
      level?: number | null
    }
    /** DeployRequest */
    DeployRequest: {
      /** Token */
      token: string
    }
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components['schemas']['ValidationError'][]
    }
    /** LoginRequest */
    LoginRequest: {
      /**
       * Identity
       * @description 邮箱或用户名
       */
      identity: string
      /**
       * Password
       * @description 密码
       */
      password: string
    }
    /** RefreshRequest */
    RefreshRequest: {
      /**
       * Refresh Token
       * @description Refresh token
       */
      refresh_token: string
    }
    /** RegisterRequest */
    RegisterRequest: {
      /**
       * Email
       * @description 邮箱
       */
      email: string
      /**
       * Username
       * @description 用户名
       */
      username: string
      /**
       * Password
       * @description 密码
       */
      password: string
    }
    /** TemplateCreate */
    TemplateCreate: {
      /** Name */
      name: string
      /**
       * Components
       * @default []
       */
      components: {
        [key: string]: unknown
      }[]
      /**
       * Refresh Interval
       * @default 30
       */
      refresh_interval: number
    }
    /** TemplateUpdate */
    TemplateUpdate: {
      /** Name */
      name?: string | null
      /** Components */
      components?:
        | {
            [key: string]: unknown
          }[]
        | null
      /** Refresh Interval */
      refresh_interval?: number | null
    }
    /** UpdateConfigRequest */
    UpdateConfigRequest: {
      /**
       * Value
       * @description 配置值
       */
      value: string
    }
    /** UpdatePostRequest */
    UpdatePostRequest: {
      /**
       * Title
       * @description 标题
       */
      title?: string | null
      /**
       * Content
       * @description 正文内容
       */
      content?: string | null
    }
    /** UpdateUserRequest */
    UpdateUserRequest: {
      /**
       * Level
       * @description 用户等级
       */
      level?: number | null
      /**
       * Is Active
       * @description 是否启用
       */
      is_active?: boolean | null
    }
    /** ValidationError */
    ValidationError: {
      /** Location */
      loc: (string | number)[]
      /** Message */
      msg: string
      /** Error Type */
      type: string
      /** Input */
      input?: unknown
      /** Context */
      ctx?: Record<string, never>
    }
  }
  responses: never
  parameters: never
  requestBodies: never
  headers: never
  pathItems: never
}
export type $defs = Record<string, never>
export interface operations {
  register_api_auth_register_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RegisterRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  login_api_auth_login_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['LoginRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  logout_api_auth_logout_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  get_me_api_auth_me_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  refresh_api_auth_refresh_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RefreshRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_users_api_auth_users_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
        /** @description 状态过滤：active/disabled */
        status?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_user_api_auth_users__user_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  update_user_api_auth_users__user_id__put: {
    parameters: {
      query?: never
      header?: never
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['UpdateUserRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_user_api_auth_users__user_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  disable_user_api_auth_users__user_id__disable_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  enable_user_api_auth_users__user_id__enable_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  admin_create_user_api_auth_admin_users_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateUserRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  trigger_deploy_api_deploy_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['DeployRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_templates_api_monitor_templates_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': {
            [key: string]: unknown
          }[]
        }
      }
    }
  }
  create_template_api_monitor_templates_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['TemplateCreate']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': {
            [key: string]: unknown
          }
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_template_api_monitor_templates__template_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        template_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': {
            [key: string]: unknown
          }
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  update_template_api_monitor_templates__template_id__put: {
    parameters: {
      query?: never
      header?: never
      path: {
        template_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['TemplateUpdate']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': {
            [key: string]: unknown
          }
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_template_api_monitor_templates__template_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        template_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': {
            [key: string]: string
          }
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_component_data_api_monitor_components__component_id__data_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        component_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': {
            [key: string]: unknown
          }
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_posts_api_blog_posts_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
        /** @description 排序字段 */
        sort_by?: string
        /** @description 搜索关键词（标题+内容） */
        q?: string | null
        /** @description 按标签筛选 */
        tag?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_post_api_blog_posts_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreatePostRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_post_by_id_api_blog_posts_by_id__post_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_post_api_blog_posts__slug__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        slug: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_my_posts_api_blog_my_posts_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
        /** @description 状态过滤：pending/published/rejected/draft */
        status?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  update_post_api_blog_posts__post_id__put: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['UpdatePostRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_post_api_blog_posts__post_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_comments_api_blog_posts__post_id__comments_get: {
    parameters: {
      query?: {
        page?: number
        page_size?: number
      }
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_comment_api_blog_posts__post_id__comments_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateCommentRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  toggle_like_api_blog_posts__post_id__like_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_pending_posts_api_blog_moderation_pending_get: {
    parameters: {
      query?: {
        page?: number
        page_size?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  approve_post_api_blog_moderation__post_id__approve_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  reject_post_api_blog_moderation__post_id__reject_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  batch_approve_posts_api_blog_moderation_batch_approve_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['BatchModerationRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  batch_reject_posts_api_blog_moderation_batch_reject_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['BatchModerationRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  add_favorite_api_blog_favorites__post_id__post: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  remove_favorite_api_blog_favorites__post_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_favorites_api_blog_favorites_get: {
    parameters: {
      query?: {
        page?: number
        page_size?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_favorite_status_api_blog_posts__post_id__favorite_status_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_report_api_blog_reports_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateReportRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  import_post_api_blog_import_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'multipart/form-data': components['schemas']['Body_import_post_api_blog_import_post']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_tags_api_blog_tags_get: {
    parameters: {
      query?: {
        page?: number
        page_size?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_tag_api_blog_tags_post: {
    parameters: {
      query: {
        /** @description 标签名 */
        name: string
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_posts_by_tag_api_blog_posts_by_tag__tag_name__get: {
    parameters: {
      query?: {
        page?: number
        page_size?: number
      }
      header?: never
      path: {
        tag_name: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_post_tags_api_blog_posts__post_id__tags_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  add_tag_to_post_api_blog_posts__post_id__tags_post: {
    parameters: {
      query: {
        name: string
      }
      header?: never
      path: {
        post_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  remove_tag_from_post_api_blog_posts__post_id__tags__tag_name__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        post_id: string
        tag_name: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_stats_api_cloud_stats_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  list_jobs_api_cloud_jobs_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
        /** @description 状态过滤 */
        status?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_job_api_cloud_jobs_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateJobRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_job_api_cloud_jobs__job_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_job_api_cloud_jobs__job_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  start_job_api_cloud_jobs__job_id__start_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  stop_job_api_cloud_jobs__job_id__stop_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  complete_job_api_cloud_jobs__job_id__complete_post: {
    parameters: {
      query?: {
        /** @description 结果路径 */
        result_path?: string | null
      }
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  fail_job_api_cloud_jobs__job_id__fail_post: {
    parameters: {
      query: {
        /** @description 错误信息 */
        error_message: string
      }
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_job_logs_api_cloud_jobs__job_id__logs_get: {
    parameters: {
      query?: {
        /** @description 日志行数 */
        lines?: number
      }
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_instances_api_cloud_jobs__job_id__instances_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
      }
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_instance_api_cloud_jobs__job_id__instances_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateInstanceRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  start_instance_api_cloud_instances__instance_id__start_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        instance_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  stop_instance_api_cloud_instances__instance_id__stop_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        instance_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_costs_api_cloud_costs_get: {
    parameters: {
      query?: {
        /** @description 按任务 ID 过滤 */
        job_id?: string | null
        /** @description 起始日期 ISO 8601 */
        start_date?: string | null
        /** @description 结束日期 ISO 8601 */
        end_date?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_gpu_metrics_api_cloud_instances__instance_id__gpu_metrics_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        instance_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  launch_job_api_cloud_jobs__job_id__launch_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_job_progress_api_cloud_jobs__job_id__progress_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_job_steps_api_cloud_jobs__job_id__steps_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        job_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_datasets_api_cloud_datasets_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
        /** @description 按来源过滤 */
        source?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_dataset_api_cloud_datasets_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateDatasetRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_dataset_api_cloud_datasets__dataset_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        dataset_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_dataset_api_cloud_datasets__dataset_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        dataset_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  sync_dataset_api_cloud_datasets__dataset_id__sync_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        dataset_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_repos_api_cloud_repos_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  create_repo_api_cloud_repos_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateCodeRepoRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_repo_api_cloud_repos__repo_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        repo_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  sync_repo_api_cloud_repos__repo_id__sync_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        repo_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_artifacts_api_cloud_artifacts_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
        /** @description 按训练任务过滤 */
        job_id?: string | null
        /** @description 按制品类型过滤：checkpoint/log/config */
        artifact_type?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_artifact_api_cloud_artifacts__artifact_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        artifact_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_artifact_api_cloud_artifacts__artifact_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        artifact_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  download_artifact_api_cloud_artifacts__artifact_id__download_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        artifact_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_configs_api_admin_config_get: {
    parameters: {
      query?: {
        group?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_config_api_admin_config__key__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        key: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  update_config_api_admin_config__key__put: {
    parameters: {
      query?: never
      header?: never
      path: {
        key: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['UpdateConfigRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_groups_api_admin_config_groups_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  reload_config_api_admin_config_reload_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  get_health_status_api_github_health_status_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  proxy_raw_api_github_raw__path__get: {
    parameters: {
      query?: {
        mode?: string
      }
      header?: never
      path: {
        path: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  clear_cache_api_github_cache_clear_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  proxy_github_get_api_github__path__get: {
    parameters: {
      query?: {
        mode?: string
      }
      header?: never
      path: {
        path: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  proxy_github_put_api_github__path__put: {
    parameters: {
      query?: {
        mode?: string
      }
      header?: never
      path: {
        path: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  proxy_github_post_api_github__path__post: {
    parameters: {
      query?: {
        mode?: string
      }
      header?: never
      path: {
        path: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  proxy_github_delete_api_github__path__delete: {
    parameters: {
      query?: {
        mode?: string
      }
      header?: never
      path: {
        path: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  proxy_github_patch_api_github__path__patch: {
    parameters: {
      query?: {
        mode?: string
      }
      header?: never
      path: {
        path: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  upload_file_api_oss_upload_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'multipart/form-data': components['schemas']['Body_upload_file_api_oss_upload_post']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  download_file_api_oss_files__file_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        file_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  delete_file_api_oss_files__file_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        file_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_my_files_api_oss_my_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  external_upload_api_oss_external__tenant_id__upload_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        tenant_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'multipart/form-data': components['schemas']['Body_external_upload_api_oss_external__tenant_id__upload_post']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_external_files_api_oss_external__tenant_id__files_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path: {
        tenant_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_storage_stats_api_oss_storage_stats_get: {
    parameters: {
      query?: {
        user_scope?: boolean
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_quota_api_oss_quota_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  trigger_eviction_api_oss_admin_evict_post: {
    parameters: {
      query?: {
        days?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  list_user_quotas_api_oss_admin_quotas_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  update_user_quota_api_oss_admin_quotas__user_id__put: {
    parameters: {
      query?: never
      header?: never
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_rate_limit_config_api_oss_admin_rate_limit_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  update_global_rate_limit_api_oss_admin_rate_limit_put: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  update_user_speed_multiplier_api_oss_admin_rate_limit_users__user_id__put: {
    parameters: {
      query?: never
      header?: never
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  admin_list_files_api_oss_admin_files_get: {
    parameters: {
      query?: {
        user_id?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  admin_delete_file_api_oss_admin_files__file_id__delete: {
    parameters: {
      query?: never
      header?: never
      path: {
        file_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  admin_stats_api_oss_admin_stats_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  top_users_by_storage_api_oss_admin_stats_top_users_get: {
    parameters: {
      query?: {
        limit?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_summary_api_system_summary_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  get_cpu_api_system_cpu_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  get_memory_api_system_memory_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  get_disk_api_system_disk_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  get_network_api_system_network_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  get_history_api_system_history_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_processes_api_system_processes_get: {
    parameters: {
      query?: {
        /** @description 排序字段：cpu_percent/memory_percent/pid/create_time */
        sort_by?: string
        /** @description 返回数量上限 */
        limit?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_status_api_crawler_status_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  start_crawler_api_crawler_start_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  stop_crawler_api_crawler_stop_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  list_records_api_crawler_records_get: {
    parameters: {
      query?: {
        page?: number
        page_size?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_record_api_crawler_records__record_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        record_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_record_file_api_crawler_records__record_id__file_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        record_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_seeds_api_crawler_seeds_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  add_seed_api_crawler_seeds_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['AddSeedRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_blacklist_api_crawler_blacklist_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  add_blacklist_api_crawler_blacklist_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['AddBlacklistRequest']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_stats_api_crawler_stats_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  list_assets_api_assets_get: {
    parameters: {
      query?: {
        /** @description 页码 */
        page?: number
        /** @description 每页数量 */
        page_size?: number
        /** @description 资产类型过滤 */
        asset_type?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  search_assets_api_assets_search_get: {
    parameters: {
      query: {
        /** @description 搜索关键词 */
        keyword: string
        /** @description 资产类型过滤 */
        asset_type?: string | null
        /** @description 起始时间 ISO 8601 */
        date_from?: string | null
        /** @description 结束时间 ISO 8601 */
        date_to?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['HTTPValidationError']
        }
      }
    }
  }
  get_asset_stats_api_assets_stats_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
}
