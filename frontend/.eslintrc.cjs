module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: [
    // ESLint推荐规则
    'eslint:recommended',
    // Vue 3推荐规则
    'plugin:vue/vue3-recommended',
    // 导入排序
    'plugin:import/recommended',
    // 禁用与Prettier冲突的规则
    'prettier',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: false,
    },
  },
  plugins: [
    'vue',
    'import',
    'unused-imports',
  ],
  settings: {
    'import/resolver': {
      alias: {
        map: [
          ['@', './src'],
        ],
        extensions: ['.js', '.vue', '.json'],
      },
    },
    'import/core-modules': ['node:url', 'node:path', 'node:fs'],
  },
  rules: {
    // ===== ESLint基础规则 =====
    // 控制台日志（生产环境警告，开发环境允许）
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    
    // 未使用变量（允许以下划线开头的参数）
    'no-unused-vars': 'off', // 使用unused-imports插件代替
    
    // 优先使用const/let
    'no-var': 'error',
    'prefer-const': 'error',
    
    // 使用严格相等
    'eqeqeq': ['error', 'always', { null: 'ignore' }],
    
    // 避免使用eval
    'no-eval': 'error',
    'no-implied-eval': 'error',
    
    // 避免使用with
    'no-with': 'error',
    
    // 避免重复导入
    'no-duplicate-imports': 'error',
    
    // 使用模板字符串
    'prefer-template': 'error',
    
    // 箭头函数简写
    'arrow-body-style': ['error', 'as-needed'],
    
    // 对象简写
    'object-shorthand': ['error', 'always'],
    
    // ===== Vue规则 =====
    // 组件名多词限制（关闭，允许单词组件名）
    'vue/multi-word-component-names': 'off',
    
    // 允许v-html（用于富文本渲染）
    'vue/no-v-html': 'off',
    
    // 属性顺序
    'vue/attributes-order': ['warn', {
      order: [
        'DEFINITION',
        'LIST_RENDERING',
        'CONDITIONALS',
        'RENDER_MODIFIERS',
        'GLOBAL',
        'UNIQUE',
        'TWO_WAY_BINDING',
        'OTHER_DIRECTIVES',
        'OTHER_ATTR',
        'EVENTS',
        'CONTENT',
      ],
    }],
    
    // 组件标签顺序
    'vue/order-in-components': ['error', {
      order: [
        'el',
        'name',
        'key',
        'parent',
        'functional',
        ['delimiters', 'comments'],
        ['components', 'directives', 'filters'],
        'extends',
        'mixins',
        ['provide', 'inject'],
        'ROUTER_GUARDS',
        'layout',
        'middleware',
        'validate',
        'scrollToTop',
        'transition',
        'loading',
        'inheritAttrs',
        'model',
        ['props', 'propsData'],
        'emits',
        'setup',
        'asyncData',
        'data',
        'fetch',
        'head',
        'computed',
        'watch',
        'watchQuery',
        'LIFECYCLE_HOOKS',
        'methods',
        ['template', 'render'],
        'renderError',
      ],
    }],
    
    // 必须使用组合式API
    'vue/component-api-style': ['error', ['script-setup', 'composition']],
    
    // 属性连字符
    'vue/attribute-hyphenation': ['error', 'always'],
    
    // 模板缩进
    'vue/html-indent': ['error', 2],
    
    // 自闭合标签
    'vue/html-self-closing': ['error', {
      html: {
        void: 'always',
        normal: 'never',
        component: 'always',
      },
      svg: 'always',
      math: 'always',
    }],
    
    // 每行最大属性数
    'vue/max-attributes-per-line': ['error', {
      singleline: 3,
      multiline: 1,
    }],
    
    // 必须默认导出
    'vue/require-default-export': 'error',
    
    // 类型化的props
    'vue/require-prop-types': 'error',
    
    // 默认的prop值
    'vue/require-default-prop': 'warn',
    
    // 有效的v-for key
    'vue/require-v-for-key': 'error',
    
    // 有效的template key
    'vue/valid-v-for': 'error',
    
    // ===== 导入规则 =====
    // 自动删除未使用的导入
    'unused-imports/no-unused-imports': 'error',
    'unused-imports/no-unused-vars': [
      'warn',
      {
        vars: 'all',
        varsIgnorePattern: '^_',
        args: 'after-used',
        argsIgnorePattern: '^_',
      },
    ],
    
    // 导入排序
    'import/order': [
      'error',
      {
        groups: [
          'builtin',
          'external',
          'internal',
          'parent',
          'sibling',
          'index',
          'object',
          'type',
        ],
        pathGroups: [
          {
            pattern: 'vue',
            group: 'external',
            position: 'before',
          },
          {
            pattern: '@/**',
            group: 'internal',
            position: 'after',
          },
        ],
        pathGroupsExcludedImportTypes: ['vue'],
        'newlines-between': 'always',
        alphabetize: {
          order: 'asc',
          caseInsensitive: true,
        },
      },
    ],
    
    // 导入扩展名
    'import/extensions': [
      'error',
      'ignorePackages',
      {
        js: 'always',
        vue: 'always',
      },
    ],
    
    // 首选默认导出
    'import/prefer-default-export': 'off',
    
    // 命名导出
    'import/no-named-default': 'error',
  },
  overrides: [
    {
      files: ['**/*.test.js', '**/*.spec.js', 'tests/**/*'],
      env: {
        jest: true,
      },
      rules: {
        'no-console': 'off',
      },
    },
    {
      files: ['cypress/**/*'],
      globals: {
        cy: 'readonly',
        Cypress: 'readonly',
      },
    },
  ],
  globals: {
    defineProps: 'readonly',
    defineEmits: 'readonly',
    defineExpose: 'readonly',
    withDefaults: 'readonly',
  },
}
