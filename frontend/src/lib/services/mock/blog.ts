import type { MockBlogData } from './types'

export const blogMockData: MockBlogData = {
  posts: [
    {
      id: 'demo-1',
      slug: 'demo-spring-notes',
      title: '春日来信：把普通日子写成可回放的片段',
      content:
        '这是首页示例内容。接口暂不可用时，用它来保证首屏轮播和列表不空白。你可以把生活中那些没有"结果"的瞬间，写成会发光的过程。',
      tags: ['时光', '生活观察'],
      author_username: '锦年志编辑部',
      views: 3251,
      likes: 248,
      created_at: '2026-04-01'
    },
    {
      id: 'demo-2',
      slug: 'demo-midnight-reading',
      title: '午夜阅读手记：在慢节奏里重建表达力',
      content:
        '你不需要一次写完一个伟大故事，只要每天留下三行真实感受。时间会把这些片段自动拼成你的个人年鉴。',
      tags: ['阅读', '成长记录'],
      author_username: '林深',
      views: 2987,
      likes: 206,
      created_at: '2026-03-28'
    },
    {
      id: 'demo-3',
      slug: 'demo-city-walk',
      title: '城市漫游计划：一张地图，七天观察练习',
      content:
        '用"地点-人物-情绪"三要素去记录城市，每一次散步都能变成创作素材。这是一个可复制的轻量化习惯模型。',
      tags: ['旅行笔记', '创作灵感'],
      author_username: '阿野',
      views: 2654,
      likes: 192,
      created_at: '2026-03-20'
    },
    {
      id: 'demo-4',
      slug: 'demo-photo-story',
      title: '影像日志模板：一图一句，建立你的视觉年轮',
      content: '拍照不只是"打卡"，更是构建记忆的索引系统。示例模板可直接套用到每日记录与项目复盘。',
      tags: ['摄影', '学习札记'],
      author_username: '苏河',
      views: 2338,
      likes: 176,
      created_at: '2026-03-12'
    },
    {
      id: 'demo-5',
      slug: 'demo-dev-journal',
      title: '工程师也写生活：把技术思维变成日常叙事',
      content:
        '把"问题-假设-验证"这种工程习惯迁移到生活记录，你会更容易看见成长轨迹，也更容易持续输出。',
      tags: ['技术实践', '心情随笔'],
      author_username: '南渡',
      views: 2140,
      likes: 153,
      created_at: '2026-03-05'
    },
    {
      id: 'demo-6',
      slug: 'demo-weekly-review',
      title: '周记复盘法：15 分钟完成一周沉淀',
      content:
        '每周固定一个时间窗口，把高光、低谷和改进点写下来。长期坚持后，你会得到一份极具个人价值的成长档案。',
      tags: ['成长记录', '学习札记'],
      author_username: '岚',
      views: 1986,
      likes: 139,
      created_at: '2026-02-27'
    }
  ],

  exploreItems: [
    {
      id: 1,
      title: '春日河畔散记',
      author: '林深',
      tags: ['时光', '生活观察'],
      date: '2026-04-28',
      likes: 36,
      favorites: 12,
      content:
        '清晨的河面有一层薄雾，风从桥洞里穿过来，带着一点潮湿和青草气息。沿着石阶慢慢往下走，脚边的水纹被阳光切成碎片。后来我在长椅上坐了很久，看骑行的人一阵阵掠过，像时间被不断轻轻翻页。傍晚回程时，天空变成温柔的橙灰色，城市一下子慢下来。',
      excerpt: '记录周末在河边散步时的光影与心绪。',
      cover: 'linear-gradient(135deg, #f2dfc7, #dcbca0)'
    },
    {
      id: 2,
      title: '晚风与胶片',
      author: '青禾',
      tags: ['摄影', '时光'],
      date: '2026-04-18',
      likes: 92,
      favorites: 48,
      content:
        '那卷过期胶片在抽屉里躺了很久，冲洗出来的时候颗粒比预期更粗，色偏也很明显。可正是这种不稳定，让街角霓虹和路人的背影都像旧电影的片段。拍摄那天风很大，手抖得厉害，很多画面轻微虚焦，却意外地贴近记忆里的真实感。',
      excerpt: '一卷过期胶片拍出的意外颗粒感，反而更贴近记忆。',
      cover: 'linear-gradient(135deg, #d9c8b0, #9f8169)'
    },
    {
      id: 3,
      title: '学习札记：响应式布局',
      author: '苏河',
      tags: ['学习札记', '技术实践'],
      date: '2026-03-29',
      likes: 57,
      favorites: 21,
      content:
        '这次把页面从固定栅格改成响应式之后，最大的感受是"先定义结构，再谈样式"。我把主体分成导航、内容、辅助区三层，并用最小断点逐步增强，而不是一开始追求大屏精致。这样做的好处是，小屏体验稳定，大屏只是在此基础上获得更舒展的排版。',
      excerpt: '从网格到弹性布局，整理一套可复用的页面骨架。',
      cover: 'linear-gradient(135deg, #e8d7bf, #c0a688)'
    },
    {
      id: 4,
      title: '山城夜色速写',
      author: '阿野',
      tags: ['旅行笔记', '生活观察'],
      date: '2026-03-03',
      likes: 18,
      favorites: 9,
      content:
        '山城的夜色总带一点潮气，霓虹在坡道和台阶上被拉成长条，像湿润空气里的荧光笔触。站在高处往下看，车灯沿着弯路缓慢流动，远处偶尔传来模糊的音乐和人声。很多瞬间并不壮观，却有一种很私人的安静感，适合被慢慢记下来。',
      excerpt: '潮湿空气里的霓虹像被晕开的颜料。',
      cover: 'linear-gradient(135deg, #d0c2b1, #8f7560)'
    }
  ],

  tags: [
    '全部',
    '时光',
    '成长记录',
    '学习札记',
    '生活观察',
    '创作灵感',
    '技术实践',
    '旅行笔记',
    '摄影',
    '电影',
    '阅读',
    '心情随笔'
  ],

  authors: [
    '全部作者',
    '锦年志编辑部',
    '林深',
    '阿野',
    '苏河',
    '南渡',
    '岚',
    '青禾',
    '江月',
    '秋迟'
  ]
}
