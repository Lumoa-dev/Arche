// ── commitlint 配置：Conventional Commits ─────────────────────
// 提交格式：type(scope): description
//   fix(auth): 修复 token 刷新并发问题
//   feat(blog): 新增标签云
//   refactor(frontend): 统一色值为 CSS 变量

const config = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'refactor',
        'perf',
        'style',
        'test',
        'docs',
        'ci',
        'chore',
        'revert',
        'build',
        'security',
      ],
    ],
    'scope-enum': [
      2,
      'always',
      [
        'backend',
        'frontend',
        'auth',
        'blog',
        'oss',
        'crawler',
        'cloud',
        'search',
        'monitor',
        'github-proxy',
        'config',
        'system-monitor',
        'asset-mgmt',
        'core',
        'deploy',
        'ci',
        'deps',
        'release',
      ],
    ],
    'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
    'header-max-length': [2, 'always', 100],
  },
  helpUrl:
    'https://github.com/conventional-commit/commitlint/#what-is-commitlint',
}

module.exports = config
