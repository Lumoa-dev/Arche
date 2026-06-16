import type { RouteRecordRaw } from 'vue-router'
import Home from '@/views/home/Home.vue'
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import PostDetail from '@/views/post-detail/PostDetail.vue'
import Explore from '@/views/explore/Explore.vue'
import About from '@/views/About.vue'
import CreateIndex from '@/views/create/index.vue'
import Assets from '@/views/Assets.vue'
import Scheduler from '@/views/Scheduler.vue'
import GitHub from '@/views/GitHub.vue'
import NotFound from '@/views/NotFound.vue'
import Forbidden from '@/views/Forbidden.vue'

export const staticRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: {
      pageName: 'home',
      layout: 'guest',
      requiresAuth: false,
      searchScope: { type: 'post', placeholder: '搜索文章...', label: '文章' }
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { layout: 'guest', requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { layout: 'guest', requiresAuth: false }
  },
  {
    path: '/explore',
    name: 'Explore',
    component: Explore,
    meta: {
      pageName: 'explore',
      layout: 'guest',
      requiresAuth: false,
      searchScope: { type: 'post', placeholder: '搜索文章标题或 ID...', label: '文章' }
    }
  },
  {
    path: '/about',
    name: 'About',
    component: About,
    meta: { layout: 'guest', requiresAuth: false }
  },
  {
    path: '/create',
    name: 'Create',
    component: CreateIndex,
    meta: {
      pageName: 'create',
      title: '创作',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'post', placeholder: '搜索文章...', label: '文章' }
    }
  },
  {
    path: '/create/editor',
    name: 'PostEditor',
    component: () => import('@/views/create/editor.vue'),
    meta: {
      pageName: 'create',
      title: '编辑器',
      layout: 'guest',
      requiresAuth: true
    }
  },
  {
    path: '/create/preview',
    name: 'PostPreview',
    component: () => import('@/views/create/preview.vue'),
    meta: {
      pageName: 'create',
      title: '预览',
      layout: 'guest',
      requiresAuth: true
    }
  },
  {
    path: '/assets',
    name: 'Assets',
    component: Assets,
    meta: {
      pageName: 'assets',
      title: '素材库',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'asset', placeholder: '搜索素材...', label: '素材' }
    }
  },
  {
    path: '/scheduler',
    name: 'Scheduler',
    component: Scheduler,
    meta: {
      pageName: 'scheduler',
      title: '调度器',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'task', placeholder: '搜索任务...', label: '任务' }
    }
  },
  {
    path: '/github',
    name: 'GitHub',
    component: GitHub,
    meta: { title: 'GitHub', layout: 'guest', requiresAuth: false }
  },
  {
    path: '/blog/:slug',
    name: 'PostDetail',
    component: PostDetail,
    meta: { layout: 'guest', requiresAuth: false }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/user/Profile.vue'),
    meta: {
      pageName: 'profile',
      title: '个人中心',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'user', placeholder: '搜索个人内容...', label: '个人' }
    }
  },
  {
    path: '/posts',
    name: 'Posts',
    component: () => import('@/views/user/Posts.vue'),
    meta: {
      pageName: 'posts',
      title: '我的文章',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'post', placeholder: '搜索我的文章...', label: '文章' }
    }
  },
  {
    path: '/posts/new',
    redirect: '/create/editor',
    meta: { requiresAuth: true }
  },
  {
    path: '/posts/:id/edit',
    redirect: (to) => ({ path: '/create/editor', query: { postId: to.params.id as string } }),
    meta: { requiresAuth: true }
  },
  {
    path: '/creator',
    name: 'CreatorDashboard',
    component: () => import('@/views/user/CreatorDashboard.vue'),
    meta: {
      pageName: 'creator',
      title: '创作者看板',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'post', placeholder: '搜索创作内容...', label: '创作' }
    }
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: Forbidden,
    meta: { title: '无权限访问', layout: 'guest', requiresAuth: false }
  },
  {
    path: '/404',
    name: 'NotFound',
    component: NotFound,
    meta: { title: '页面未找到', layout: 'guest', requiresAuth: false }
  },
  // ====== 控制台 & 管理后台（嵌套路由，侧边栏不销毁） ======
  {
    path: '/console',
    component: () => import('@/components/widgets/common/ConsoleShell.vue'),
    meta: { layout: 'guest', requiresAuth: true, level: 0 },
    children: [
      {
        path: '',
        name: 'Console',
        component: () => import('@/views/user/Console.vue'),
        meta: {
          pageName: 'console',
          title: '控制台首页',
          searchScope: { type: 'console', placeholder: '搜索控制台功能或资源...', label: '控制台' }
        }
      },
      {
        path: '/admin/users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/users-overview/UsersOverview.vue'),
        meta: {
          pageName: 'admin_users',
          title: '用户管理',
          searchScope: { type: 'user', placeholder: '搜索用户...', label: '用户' }
        }
      },
      {
        path: '/admin/content',
        name: 'AdminContent',
        component: () => import('@/views/admin/content-overview/ContentOverview.vue'),
        meta: {
          pageName: 'admin_content',
          title: '内容管理',
          searchScope: { type: 'content', placeholder: '搜索内容...', label: '内容' }
        }
      },
      {
        path: '/admin/ops',
        name: 'AdminOps',
        component: () => import('@/views/admin/ops-overview/OpsOverview.vue'),
        meta: {
          pageName: 'admin_ops',
          title: '运维管理',
          searchScope: { type: 'ops', placeholder: '搜索运维资源...', label: '运维' }
        }
      },
      // 子页面
      {
        path: '/admin/users/list',
        name: 'AdminUsersList',
        component: () => import('@/views/admin/users/Users.vue'),
        meta: {
          pageName: 'admin_users',
          title: '用户列表',
          searchScope: { type: 'user', placeholder: '搜索用户名、邮箱或 ID...', label: '用户' }
        }
      },
      {
        path: '/admin/users/assets',
        name: 'AdminUsersAssets',
        component: () => import('@/views/admin/assets-overview/AssetsOverview.vue'),
        meta: {
          pageName: 'admin_users',
          title: '资产管理',
          searchScope: { type: 'asset', placeholder: '搜索资产...', label: '资产' }
        }
      },
      {
        path: '/admin/content/moderation',
        name: 'AdminContentModeration',
        component: () => import('@/views/admin/moderation-posts/ModerationPosts.vue'),
        meta: {
          pageName: 'admin_content',
          title: '帖子审核',
          searchScope: { type: 'content', placeholder: '搜索待审核内容...', label: '审核' }
        }
      },
      {
        path: '/admin/ops/system',
        name: 'AdminOpsSystem',
        component: () => import('@/views/admin/system-monitor/SystemMonitor.vue'),
        meta: {
          pageName: 'admin_ops',
          title: '系统监控',
          searchScope: { type: 'ops', placeholder: '搜索系统指标...', label: '系统' }
        }
      },
      {
        path: '/admin/ops/storage',
        name: 'AdminOpsStorage',
        component: () => import('@/views/admin/quota-management/QuotaManagement.vue'),
        meta: {
          pageName: 'admin_ops',
          title: 'OSS 存储管理',
          searchScope: { type: 'asset', placeholder: '搜索存储资源...', label: '存储' }
        }
      },
      {
        path: '/admin/ops/config',
        name: 'AdminOpsConfig',
        component: () => import('@/views/admin/config-admin/ConfigAdmin.vue'),
        meta: {
          pageName: 'admin_ops',
          title: '运行时配置',
          searchScope: { type: 'ops', placeholder: '搜索配置项...', label: '配置' }
        }
      },
      {
        path: '/admin/ops/ip-ban',
        name: 'AdminOpsIpBan',
        component: () => import('@/views/admin/ip-ban/IpBanOverview.vue'),
        meta: {
          pageName: 'admin_ops',
          title: 'IP 封禁管理',
          searchScope: { type: 'ops', placeholder: '搜索 IP...', label: 'IP 封禁' }
        }
      },
      {
        path: '/admin/ops/ip-ban/list',
        name: 'AdminOpsIpBanList',
        component: () => import('@/views/admin/ip-ban/IpBanManagement.vue'),
        meta: {
          pageName: 'admin_ops',
          title: '封禁列表',
          searchScope: { type: 'ops', placeholder: '搜索 IP/CIDR...', label: 'IP 封禁' }
        }
      },
      {
        path: '/admin/ops/ip-ban/logs',
        name: 'AdminOpsIpBanLogs',
        component: () => import('@/views/admin/ip-ban/IpBanLogs.vue'),
        meta: {
          pageName: 'admin_ops',
          title: '封禁日志',
          searchScope: { type: 'ops', placeholder: '搜索操作记录...', label: '操作日志' }
        }
      },
      {
        path: '/admin/ops/ip-ban/rules',
        name: 'AdminOpsIpBanRules',
        component: () => import('@/views/admin/ip-ban/IpBanRules.vue'),
        meta: {
          pageName: 'admin_ops',
          title: '自动封禁规则',
          searchScope: { type: 'ops', placeholder: '搜索规则...', label: '封禁规则' }
        }
      },
      // 权限管理
      {
        path: '/admin/permissions',
        name: 'AdminPermissions',
        component: () => import('@/views/admin/permission-editor/PermissionEditor.vue'),
        meta: {
          pageName: 'admin_permissions',
          title: '权限配置',
          searchScope: { type: 'ops', placeholder: '搜索页面或组件...', label: '权限' }
        }
      },
      {
        path: '/admin/ops/request-logs',
        name: 'AdminRequestLogs',
        component: () => import('@/views/admin/request-log/RequestLogView.vue'),
        meta: {
          pageName: 'admin_ops',
          title: 'IP 请求日志',
          searchScope: { type: 'ops', placeholder: '搜索 IP 或行为分类...', label: '请求日志' }
        }
      }
    ]
  },
  // ====== 托管任务 ======
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/tasks/Tasks.vue'),
    meta: {
      pageName: 'tasks',
      title: '托管任务',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'task', placeholder: '搜索任务...', label: '任务' }
    }
  },
  {
    path: '/tasks/crawler',
    name: 'TasksCrawler',
    component: () => import('@/views/tasks/Crawler.vue'),
    meta: {
      pageName: 'tasks',
      title: '爬虫管理',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'task', placeholder: '搜索爬虫任务...', label: '爬虫' }
    }
  },
  {
    path: '/tasks/cloud',
    name: 'TasksCloud',
    component: () => import('@/views/tasks/Cloud.vue'),
    meta: {
      pageName: 'tasks',
      title: '云训练管理',
      layout: 'guest',
      requiresAuth: true,
      searchScope: { type: 'task', placeholder: '搜索训练任务...', label: '训练' }
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404',
    meta: { layout: 'guest', requiresAuth: false }
  }
]
