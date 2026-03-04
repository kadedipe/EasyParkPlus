// ============================================
// ESLINT CONFIGURATION - PARKING MANAGEMENT SYSTEM FRONTEND
// ============================================
// This configuration ensures code quality and consistency
// across the React/TypeScript codebase
// ============================================

module.exports = {
  root: true,
  
  // ============================================
  // Environment
  // ============================================
  env: {
    browser: true,
    es2024: true,
    node: true,
    jest: true,
    'vitest/env': true,
    'cypress/globals': true,
  },

  // ============================================
  // Parser Configuration
  // ============================================
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
      globalReturn: false,
      impliedStrict: true,
    },
    project: ['./tsconfig.json', './tsconfig.node.json'],
    tsconfigRootDir: __dirname,
    createDefaultProgram: true,
    warnOnUnsupportedTypeScriptVersion: true,
  },

  // ============================================
  // Plugins
  // ============================================
  plugins: [
    '@typescript-eslint',
    'react',
    'react-hooks',
    'jsx-a11y',
    'import',
    'jest',
    'testing-library',
    'vitest',
    'cypress',
    'prettier',
    'promise',
    'sonarjs',
    'unicorn',
    'security',
    'optimize-regex',
    'no-secrets',
    'chai-friendly',
    'react-refresh',
  ],

  // ============================================
  // Extends (Inherit from recommended configs)
  // ============================================
  extends: [
    // ESLint recommended
    'eslint:recommended',
    
    // TypeScript
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking',
    'plugin:@typescript-eslint/strict',
    
    // React
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
    
    // Accessibility
    'plugin:jsx-a11y/recommended',
    
    // Import
    'plugin:import/recommended',
    'plugin:import/typescript',
    
    // Testing
    'plugin:jest/recommended',
    'plugin:jest/style',
    'plugin:testing-library/react',
    'plugin:vitest/recommended',
    'plugin:cypress/recommended',
    
    // Code quality
    'plugin:sonarjs/recommended',
    'plugin:unicorn/recommended',
    'plugin:promise/recommended',
    'plugin:security/recommended',
    
    // Prettier (must be last)
    'prettier',
  ],

  // ============================================
  // Settings
  // ============================================
  settings: {
    react: {
      version: 'detect',
      pragma: 'React',
      fragment: 'Fragment',
    },
    'import/resolver': {
      typescript: {
        alwaysTryTypes: true,
        project: './tsconfig.json',
      },
      node: {
        extensions: ['.js', '.jsx', '.ts', '.tsx', '.d.ts'],
        moduleDirectory: ['node_modules', 'src/'],
      },
      alias: {
        map: [
          ['@', './src'],
          ['@components', './src/components'],
          ['@pages', './src/pages'],
          ['@hooks', './src/hooks'],
          ['@services', './src/services'],
          ['@store', './src/store'],
          ['@utils', './src/utils'],
          ['@types', './src/types'],
          ['@assets', './src/assets'],
          ['@styles', './src/styles'],
        ],
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
      },
    },
    'import/ignore': ['node_modules', '\\.(css|scss|less|svg|png|jpg|webp)$'],
    'import/extensions': ['.js', '.jsx', '.ts', '.tsx'],
    'import/parsers': {
      '@typescript-eslint/parser': ['.ts', '.tsx'],
    },
    jest: {
      version: 29,
    },
    vitest: {
      typecheck: true,
    },
    'jsx-a11y': {
      polymorphicPropName: 'as',
      components: {
        Button: 'button',
        Input: 'input',
        Select: 'select',
        Textarea: 'textarea',
        Link: 'a',
        Img: 'img',
      },
    },
  },

  // ============================================
  // Custom Rules
  // ============================================
  rules: {
    // ==========================================
    // General ESLint Rules
    // ==========================================
    'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'warn',
    'no-alert': 'warn',
    'no-var': 'error',
    'prefer-const': 'error',
    'prefer-template': 'error',
    'prefer-spread': 'error',
    'prefer-rest-params': 'error',
    'prefer-destructuring': [
      'error',
      {
        array: false,
        object: true,
      },
      {
        enforceForRenamedProperties: false,
      },
    ],
    'prefer-arrow-callback': 'error',
    'arrow-body-style': ['error', 'as-needed'],
    'object-shorthand': ['error', 'always'],
    'no-unused-vars': 'off', // Use TypeScript version
    'no-use-before-define': 'off',
    'no-shadow': 'off',
    'no-param-reassign': ['error', { props: false }],
    'no-underscore-dangle': ['error', { allow: ['_id', '__REDUX_DEVTOOLS_EXTENSION__'] }],
    'no-plusplus': ['error', { allowForLoopAfterthoughts: true }],
    'no-nested-ternary': 'warn',
    'no-duplicate-imports': 'error',
    'no-return-await': 'error',
    'require-await': 'error',
    'eqeqeq': ['error', 'always', { null: 'ignore' }],
    'curly': ['error', 'all'],
    'brace-style': ['error', '1tbs', { allowSingleLine: false }],
    'comma-dangle': ['error', 'always-multiline'],
    'semi': ['error', 'always'],
    'quotes': ['error', 'single', { avoidEscape: true }],
    'max-len': [
      'warn',
      {
        code: 100,
        tabWidth: 2,
        ignoreUrls: true,
        ignoreComments: false,
        ignoreRegExpLiterals: true,
        ignoreStrings: true,
        ignoreTemplateLiterals: true,
      },
    ],
    'max-depth': ['warn', 4],
    'max-params': ['warn', 4],
    'max-lines': ['warn', { max: 500, skipBlankLines: true, skipComments: true }],
    'max-lines-per-function': [
      'warn',
      { max: 100, skipBlankLines: true, skipComments: true },
    ],
    'complexity': ['warn', 10],
    'no-restricted-syntax': [
      'error',
      {
        selector: 'ForInStatement',
        message: 'for..in loops iterate over the entire prototype chain, which is virtually never what you want. Use Object.{keys,values,entries}, and iterate over the resulting array.',
      },
      {
        selector: 'LabeledStatement',
        message: 'Labels are a form of GOTO; using them makes code confusing and hard to maintain and understand.',
      },
      {
        selector: 'WithStatement',
        message: '`with` is disallowed in strict mode because it makes code impossible to predict and optimize.',
      },
    ],

    // ==========================================
    // TypeScript Rules
    // ==========================================
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        destructuredArrayIgnorePattern: '^_',
      },
    ],
    '@typescript-eslint/no-explicit-any': ['warn', { ignoreRestArgs: true }],
    '@typescript-eslint/explicit-function-return-type': [
      'error',
      {
        allowExpressions: true,
        allowTypedFunctionExpressions: true,
        allowHigherOrderFunctions: true,
        allowDirectConstAssertionInArrowFunctions: true,
        allowConciseArrowFunctionExpressionsStartingWithVoid: true,
      },
    ],
    '@typescript-eslint/explicit-module-boundary-types': 'error',
    '@typescript-eslint/no-non-null-assertion': 'warn',
    '@typescript-eslint/no-use-before-define': ['error', { functions: false, classes: false }],
    '@typescript-eslint/no-shadow': 'error',
    '@typescript-eslint/no-floating-promises': 'error',
    '@typescript-eslint/no-misused-promises': [
      'error',
      {
        checksVoidReturn: {
          arguments: false,
          attributes: false,
          properties: false,
          returns: false,
          variables: false,
        },
      },
    ],
    '@typescript-eslint/await-thenable': 'error',
    '@typescript-eslint/no-unnecessary-type-assertion': 'error',
    '@typescript-eslint/no-unnecessary-condition': 'error',
    '@typescript-eslint/no-unnecessary-boolean-literal-compare': 'error',
    '@typescript-eslint/no-unnecessary-qualifier': 'error',
    '@typescript-eslint/no-unnecessary-type-arguments': 'error',
    '@typescript-eslint/prefer-nullish-coalescing': 'error',
    '@typescript-eslint/prefer-optional-chain': 'error',
    '@typescript-eslint/prefer-readonly': 'error',
    '@typescript-eslint/prefer-reduce-type-parameter': 'error',
    '@typescript-eslint/prefer-ts-expect-error': 'error',
    '@typescript-eslint/ban-ts-comment': [
      'error',
      {
        'ts-expect-error': 'allow-with-description',
        'ts-ignore': true,
        'ts-nocheck': true,
        'ts-check': false,
        minimumDescriptionLength: 3,
      },
    ],
    '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],
    '@typescript-eslint/consistent-type-imports': [
      'error',
      {
        prefer: 'type-imports',
        disallowTypeAnnotations: true,
        fixStyle: 'inline-type-imports',
      },
    ],
    '@typescript-eslint/consistent-type-exports': 'error',
    '@typescript-eslint/member-ordering': [
      'error',
      {
        default: [
          'signature',
          'public-static-field',
          'protected-static-field',
          'private-static-field',
          '#private-static-field',
          'public-decorated-field',
          'protected-decorated-field',
          'private-decorated-field',
          'public-instance-field',
          'protected-instance-field',
          'private-instance-field',
          '#private-instance-field',
          'public-abstract-field',
          'protected-abstract-field',
          'public-constructor',
          'protected-constructor',
          'private-constructor',
          'public-static-method',
          'protected-static-method',
          'private-static-method',
          '#private-static-method',
          'public-decorated-method',
          'protected-decorated-method',
          'private-decorated-method',
          'public-instance-method',
          'protected-instance-method',
          'private-instance-method',
          '#private-instance-method',
          'public-abstract-method',
          'protected-abstract-method',
        ],
      },
    ],
    '@typescript-eslint/naming-convention': [
      'error',
      {
        selector: 'default',
        format: ['camelCase'],
        leadingUnderscore: 'forbid',
        trailingUnderscore: 'forbid',
      },
      {
        selector: 'variable',
        format: ['camelCase', 'UPPER_CASE'],
      },
      {
        selector: 'parameter',
        format: ['camelCase'],
        leadingUnderscore: 'allow',
      },
      {
        selector: 'memberLike',
        modifiers: ['private'],
        format: ['camelCase'],
        leadingUnderscore: 'require',
      },
      {
        selector: 'typeLike',
        format: ['PascalCase'],
      },
      {
        selector: 'interface',
        format: ['PascalCase'],
        custom: {
          regex: '^I[A-Z]',
          match: false,
        },
      },
      {
        selector: 'enum',
        format: ['PascalCase'],
      },
      {
        selector: 'enumMember',
        format: ['UPPER_CASE'],
      },
    ],

    // ==========================================
    // React Rules
    // ==========================================
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
    'react/display-name': 'off',
    'react/jsx-uses-react': 'error',
    'react/jsx-uses-vars': 'error',
    'react/no-unescaped-entities': 'error',
    'react/no-unknown-property': 'error',
    'react/no-deprecated': 'error',
    'react/no-direct-mutation-state': 'error',
    'react/no-is-mounted': 'error',
    'react/no-render-return-value': 'error',
    'react/no-string-refs': 'error',
    'react/no-this-in-sfc': 'error',
    'react/no-typos': 'error',
    'react/no-unsafe': 'error',
    'react/no-unused-state': 'error',
    'react/no-access-state-in-setstate': 'error',
    'react/no-danger': 'warn',
    'react/no-danger-with-children': 'error',
    'react/no-array-index-key': 'warn',
    'react/no-children-prop': 'error',
    'react/no-find-dom-node': 'error',
    'react/self-closing-comp': [
      'error',
      {
        component: true,
        html: true,
      },
    ],
    'react/button-has-type': [
      'error',
      {
        button: true,
        submit: true,
        reset: false,
      },
    ],
    'react/destructuring-assignment': ['error', 'always'],
    'react/function-component-definition': [
      'error',
      {
        namedComponents: 'arrow-function',
        unnamedComponents: 'arrow-function',
      },
    ],
    'react/hook-use-state': 'error',
    'react/jsx-boolean-value': ['error', 'never'],
    'react/jsx-closing-bracket-location': ['error', 'line-aligned'],
    'react/jsx-closing-tag-location': 'error',
    'react/jsx-curly-brace-presence': ['error', { props: 'never', children: 'never' }],
    'react/jsx-curly-spacing': ['error', { when: 'never', children: true }],
    'react/jsx-equals-spacing': ['error', 'never'],
    'react/jsx-filename-extension': ['error', { extensions: ['.tsx'] }],
    'react/jsx-first-prop-new-line': ['error', 'multiline'],
    'react/jsx-fragments': ['error', 'syntax'],
    'react/jsx-handler-names': [
      'error',
      {
        eventHandlerPrefix: 'handle',
        eventHandlerPropPrefix: 'on',
        checkLocalVariables: true,
        checkInlineFunction: true,
      },
    ],
    'react/jsx-indent': ['error', 2],
    'react/jsx-indent-props': ['error', 2],
    'react/jsx-key': [
      'error',
      {
        checkFragmentShorthand: true,
        checkKeyMustBeforeSpread: true,
        warnOnDuplicates: true,
      },
    ],
    'react/jsx-max-props-per-line': ['error', { maximum: 3, when: 'multiline' }],
    'react/jsx-no-bind': [
      'error',
      {
        ignoreDOMComponents: false,
        ignoreRefs: false,
        allowArrowFunctions: true,
        allowFunctions: false,
        allowBind: false,
      },
    ],
    'react/jsx-no-comment-textnodes': 'error',
    'react/jsx-no-constructed-context-values': 'error',
    'react/jsx-no-duplicate-props': 'error',
    'react/jsx-no-leaked-render': ['error', { validStrategies: ['ternary'] }],
    'react/jsx-no-literals': 'off',
    'react/jsx-no-script-url': 'error',
    'react/jsx-no-target-blank': [
      'error',
      {
        allowReferrer: true,
        enforceDynamicLinks: 'always',
      },
    ],
    'react/jsx-no-undef': 'error',
    'react/jsx-no-useless-fragment': 'error',
    'react/jsx-one-expression-per-line': ['error', { allow: 'single-child' }],
    'react/jsx-pascal-case': [
      'error',
      {
        allowAllCaps: false,
        allowLeadingUnderscore: false,
        allowNamespace: true,
      },
    ],
    'react/jsx-props-no-multi-spaces': 'error',
    'react/jsx-props-no-spreading': [
      'warn',
      {
        html: 'enforce',
        custom: 'ignore',
        explicitSpread: 'ignore',
        exceptions: ['Component', 'App'],
      },
    ],
    'react/jsx-sort-props': [
      'error',
      {
        callbacksLast: true,
        shorthandFirst: true,
        shorthandLast: false,
        ignoreCase: true,
        noSortAlphabetically: false,
        reservedFirst: ['key', 'ref'],
      },
    ],
    'react/jsx-tag-spacing': [
      'error',
      {
        closingSlash: 'never',
        beforeSelfClosing: 'always',
        afterOpening: 'never',
        beforeClosing: 'never',
      },
    ],
    'react/jsx-uses-vars': 'error',
    'react/jsx-wrap-multilines': [
      'error',
      {
        declaration: 'parens-new-line',
        assignment: 'parens-new-line',
        return: 'parens-new-line',
        arrow: 'parens-new-line',
        condition: 'parens-new-line',
        logical: 'parens-new-line',
        prop: 'parens-new-line',
      },
    ],
    'react/state-in-constructor': ['error', 'never'],
    'react/static-property-placement': ['error', 'static public field'],
    'react/void-dom-elements-no-children': 'error',

    // ==========================================
    // React Hooks Rules
    // ==========================================
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': [
      'warn',
      {
        additionalHooks: '(useMyCustomHook|useAnotherHook)',
        enableDangerousAutofixThisMayCauseInfiniteLoops: false,
      },
    ],

    // ==========================================
    // React Refresh (for Fast Refresh)
    // ==========================================
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true, checkJS: true },
    ],

    // ==========================================
    // Accessibility (jsx-a11y) Rules
    // ==========================================
    'jsx-a11y/alt-text': [
      'error',
      {
        elements: ['img', 'object', 'area', 'input[type="image"]'],
        img: ['Image'],
        object: ['Object'],
        area: ['Area'],
        'input[type="image"]': ['InputImage'],
      },
    ],
    'jsx-a11y/anchor-has-content': 'error',
    'jsx-a11y/anchor-is-valid': [
      'error',
      {
        components: ['Link'],
        specialLink: ['to'],
        aspects: ['noHref', 'invalidHref', 'preferButton'],
      },
    ],
    'jsx-a11y/aria-activedescendant-has-tabindex': 'error',
    'jsx-a11y/aria-props': 'error',
    'jsx-a11y/aria-proptypes': 'error',
    'jsx-a11y/aria-role': ['error', { ignoreNonDOM: true }],
    'jsx-a11y/aria-unsupported-elements': 'error',
    'jsx-a11y/autocomplete-valid': 'error',
    'jsx-a11y/click-events-have-key-events': 'error',
    'jsx-a11y/control-has-associated-label': [
      'error',
      {
        ignoreElements: [
          'audio',
          'canvas',
          'embed',
          'input',
          'textarea',
          'tr',
          'video',
          'button',
          'select',
        ],
        ignoreRoles: [
          'grid',
          'listbox',
          'menu',
          'menubar',
          'radiogroup',
          'row',
          'tablist',
          'toolbar',
          'tree',
          'treegrid',
        ],
        includeRoles: ['alert', 'dialog'],
      },
    ],
    'jsx-a11y/heading-has-content': 'error',
    'jsx-a11y/html-has-lang': 'error',
    'jsx-a11y/iframe-has-title': 'error',
    'jsx-a11y/img-redundant-alt': 'error',
    'jsx-a11y/interactive-supports-focus': 'error',
    'jsx-a11y/label-has-associated-control': [
      'error',
      {
        labelComponents: ['Label'],
        labelAttributes: ['label'],
        controlComponents: ['Input', 'Select', 'Textarea'],
        assert: 'htmlFor',
        depth: 3,
      },
    ],
    'jsx-a11y/lang': 'error',
    'jsx-a11y/media-has-caption': 'error',
    'jsx-a11y/mouse-events-have-key-events': 'error',
    'jsx-a11y/no-access-key': 'error',
    'jsx-a11y/no-autofocus': ['error', { ignoreNonDOM: true }],
    'jsx-a11y/no-distracting-elements': [
      'error',
      {
        elements: ['marquee', 'blink'],
      },
    ],
    'jsx-a11y/no-interactive-element-to-noninteractive-role': 'error',
    'jsx-a11y/no-noninteractive-element-interactions': [
      'error',
      {
        handlers: [
          'onClick',
          'onMouseDown',
          'onMouseUp',
          'onKeyPress',
          'onKeyDown',
          'onKeyUp',
        ],
      },
    ],
    'jsx-a11y/no-noninteractive-element-to-interactive-role': 'error',
    'jsx-a11y/no-noninteractive-tabindex': 'error',
    'jsx-a11y/no-onchange': 'error',
    'jsx-a11y/no-redundant-roles': 'error',
    'jsx-a11y/no-static-element-interactions': [
      'error',
      {
        handlers: [
          'onClick',
          'onMouseDown',
          'onMouseUp',
          'onKeyPress',
          'onKeyDown',
          'onKeyUp',
        ],
      },
    ],
    'jsx-a11y/role-has-required-aria-props': 'error',
    'jsx-a11y/role-supports-aria-props': 'error',
    'jsx-a11y/scope': 'error',
    'jsx-a11y/tabindex-no-positive': 'error',

    // ==========================================
    // Import Rules
    // ==========================================
    'import/no-unresolved': ['error', { commonjs: true, amd: true }],
    'import/named': 'error',
    'import/default': 'error',
    'import/namespace': 'error',
    'import/export': 'error',
    'import/no-named-as-default': 'error',
    'import/no-named-as-default-member': 'error',
    'import/no-deprecated': 'warn',
    'import/no-extraneous-dependencies': [
      'error',
      {
        devDependencies: [
          '**/*.test.{ts,tsx}',
          '**/*.spec.{ts,tsx}',
          '**/test/**/*.{ts,tsx}',
          '**/tests/**/*.{ts,tsx}',
          '**/__tests__/**/*.{ts,tsx}',
          '**/setupTests.{ts,tsx}',
          '**/vitest.config.{ts,js}',
          '**/cypress/**/*.{ts,js}',
          '**/.eslintrc.{js,cjs}',
          '**/vite.config.{ts,js}',
        ],
        optionalDependencies: false,
      },
    ],
    'import/no-mutable-exports': 'error',
    'import/no-commonjs': 'error',
    'import/no-amd': 'error',
    'import/no-nodejs-modules': 'error',
    'import/first': 'error',
    'import/exports-last': 'off',
    'import/no-duplicates': 'error',
    'import/no-namespace': 'off',
    'import/extensions': [
      'error',
      'ignorePackages',
      {
        js: 'never',
        jsx: 'never',
        ts: 'never',
        tsx: 'never',
      },
    ],
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
            pattern: 'react',
            group: 'builtin',
            position: 'before',
          },
          {
            pattern: '@/**',
            group: 'internal',
            position: 'after',
          },
        ],
        pathGroupsExcludedImportTypes: ['react'],
        'newlines-between': 'always',
        alphabetize: {
          order: 'asc',
          caseInsensitive: true,
        },
        warnOnUnassignedImports: true,
      },
    ],
    'import/newline-after-import': ['error', { count: 1 }],
    'import/no-unassigned-import': ['error', { allow: ['**/*.css', '**/*.scss'] }],
    'import/no-named-default': 'error',
    'import/no-default-export': 'off',
    'import/no-named-export': 'off',
    'import/no-anonymous-default-export': [
      'error',
      {
        allowArray: false,
        allowArrowFunction: false,
        allowAnonymousClass: false,
        allowAnonymousFunction: false,
        allowCallExpression: true,
        allowLiteral: false,
        allowObject: false,
      },
    ],
    'import/group-exports': 'off',
    'import/dynamic-import-chunkname': 'off',

    // ==========================================
    // Jest Rules
    // ==========================================
    'jest/no-disabled-tests': 'warn',
    'jest/no-focused-tests': 'error',
    'jest/no-identical-title': 'error',
    'jest/prefer-to-have-length': 'warn',
    'jest/valid-expect': 'error',
    'jest/consistent-test-it': ['error', { fn: 'it', withinDescribe: 'it' }],
    'jest/no-test-prefixes': 'error',
    'jest/no-alias-methods': 'error',
    'jest/prefer-called-with': 'error',
    'jest/prefer-expect-assertions': 'off',
    'jest/prefer-hooks-on-top': 'error',
    'jest/prefer-spy-on': 'error',
    'jest/prefer-strict-equal': 'error',
    'jest/prefer-to-be': 'error',
    'jest/prefer-to-contain': 'error',
    'jest/prefer-to-have-length': 'error',
    'jest/require-to-throw-message': 'error',
    'jest/require-top-level-describe': 'error',
    'jest/unbound-method': 'error',

    // ==========================================
    // Testing Library Rules
    // ==========================================
    'testing-library/await-async-queries': 'error',
    'testing-library/await-async-utils': 'error',
    'testing-library/await-async-events': 'error',
    'testing-library/no-await-sync-queries': 'error',
    'testing-library/no-container': 'error',
    'testing-library/no-debugging-utils': 'warn',
    'testing-library/no-dom-import': ['error', 'react'],
    'testing-library/no-manual-cleanup': 'error',
    'testing-library/no-node-access': 'error',
    'testing-library/no-promise-in-fire-event': 'error',
    'testing-library/no-render-in-lifecycle': 'error',
    'testing-library/no-unnecessary-act': 'error',
    'testing-library/no-wait-for-empty-callback': 'error',
    'testing-library/no-wait-for-multiple-assertions': 'error',
    'testing-library/no-wait-for-side-effects': 'error',
    'testing-library/no-wait-for-snapshot': 'error',
    'testing-library/prefer-find-by': 'error',
    'testing-library/prefer-presence-queries': 'error',
    'testing-library/prefer-query-by-disappearance': 'error',
    'testing-library/prefer-screen-queries': 'error',
    'testing-library/prefer-user-event': 'error',
    'testing-library/render-result-naming-convention': 'error',

    // ==========================================
    // Cypress Rules
    // ==========================================
    'cypress/no-assigning-return-values': 'error',
    'cypress/no-unnecessary-waiting': 'error',
    'cypress/assertion-before-screenshot': 'warn',
    'cypress/no-async-tests': 'error',
    'cypress/no-pause': 'error',

    // ==========================================
    // Promise Rules
    // ==========================================
    'promise/catch-or-return': ['error', { allowFinally: true }],
    'promise/no-return-wrap': 'error',
    'promise/param-names': 'error',
    'promise/always-return': 'error',
    'promise/no-return-in-finally': 'error',
    'promise/prefer-await-to-then': 'error',
    'promise/prefer-await-to-callbacks': 'error',
    'promise/no-nesting': 'warn',
    'promise/no-promise-in-callback': 'warn',
    'promise/no-callback-in-promise': 'warn',
    'promise/valid-params': 'warn',

    // ==========================================
    // SonarJS Rules (Code Quality)
    // ==========================================
    'sonarjs/cognitive-complexity': ['error', 15],
    'sonarjs/elseif-without-else': 'error',
    'sonarjs/max-switch-cases': ['error', 10],
    'sonarjs/no-all-duplicated-branches': 'error',
    'sonarjs/no-collapsible-if': 'error',
    'sonarjs/no-collection-size-mischeck': 'error',
    'sonarjs/no-duplicate-string': ['error', { threshold: 3 }],
    'sonarjs/no-duplicated-branches': 'error',
    'sonarjs/no-element-overwrite': 'error',
    'sonarjs/no-empty-collection': 'error',
    'sonarjs/no-extra-arguments': 'error',
    'sonarjs/no-gratuitous-expressions': 'error',
    'sonarjs/no-identical-conditions': 'error',
    'sonarjs/no-identical-expressions': 'error',
    'sonarjs/no-identical-functions': 'error',
    'sonarjs/no-ignored-return': 'error',
    'sonarjs/no-inverted-boolean-check': 'error',
    'sonarjs/no-nested-switch': 'error',
    'sonarjs/no-nested-template-literals': 'error',
    'sonarjs/no-one-iteration-loop': 'error',
    'sonarjs/no-redundant-boolean': 'error',
    'sonarjs/no-redundant-jump': 'error',
    'sonarjs/no-same-line-conditional': 'error',
    'sonarjs/no-small-switch': 'error',
    'sonarjs/no-unused-collection': 'error',
    'sonarjs/no-use-of-empty-return-value': 'error',
    'sonarjs/no-useless-catch': 'error',
    'sonarjs/prefer-immediate-return': 'error',
    'sonarjs/prefer-object-literal': 'error',
    'sonarjs/prefer-single-boolean-print': 'error',
    'sonarjs/prefer-while': 'error',

    // ==========================================
    // Unicorn Rules (Modern JavaScript)
    // ==========================================
    'unicorn/better-regex': 'error',
    'unicorn/catch-error-name': ['error', { name: 'error' }],
    'unicorn/consistent-destructuring': 'error',
    'unicorn/consistent-function-scoping': 'error',
    'unicorn/custom-error-definition': 'off',
    'unicorn/empty-brace-spaces': 'error',
    'unicorn/error-message': 'error',
    'unicorn/escape-case': 'error',
    'unicorn/expiring-todo-comments': 'error',
    'unicorn/explicit-length-check': 'error',
    'unicorn/filename-case': [
      'error',
      {
        cases: {
          camelCase: true,
          pascalCase: true,
        },
      },
    ],
    'unicorn/import-index': 'error',
    'unicorn/import-style': 'error',
    'unicorn/new-for-builtins': 'error',
    'unicorn/no-abusive-eslint-disable': 'error',
    'unicorn/no-array-callback-reference': 'error',
    'unicorn/no-array-for-each': 'error',
    'unicorn/no-array-method-this-argument': 'error',
    'unicorn/no-array-push-push': 'error',
    'unicorn/no-array-reduce': 'warn',
    'unicorn/no-array-unique': 'error',
    'unicorn/no-await-expression-member': 'error',
    'unicorn/no-console-spaces': 'error',
    'unicorn/no-document-clean': 'error',
    'unicorn/no-empty-file': 'error',
    'unicorn/no-for-loop': 'error',
    'unicorn/no-hex-escape': 'error',
    'unicorn/no-instanceof-array': 'error',
    'unicorn/no-invalid-remove-event-listener': 'error',
    'unicorn/no-keyword-prefix': 'off',
    'unicorn/no-lonely-if': 'error',
    'unicorn/no-negated-condition': 'off',
    'unicorn/no-nested-ternary': 'error',
    'unicorn/no-new-array': 'error',
    'unicorn/no-new-buffer': 'error',
    'unicorn/no-null': 'off',
    'unicorn/no-object-as-default-parameter': 'error',
    'unicorn/no-process-exit': 'error',
    'unicorn/no-static-only-class': 'error',
    'unicorn/no-thenable': 'error',
    'unicorn/no-this-assignment': 'error',
    'unicorn/no-unreadable-array-destructuring': 'error',
    'unicorn/no-unreadable-iife': 'error',
    'unicorn/no-unsafe-regex': 'off',
    'unicorn/no-unused-properties': 'error',
    'unicorn/no-useless-fallback-in-spread': 'error',
    'unicorn/no-useless-length-check': 'error',
    'unicorn/no-useless-promise-resolve-reject': 'error',
    'unicorn/no-useless-spread': 'error',
    'unicorn/no-useless-undefined': 'error',
    'unicorn/no-zero-fractions': 'error',
    'unicorn/number-literal-case': 'error',
    'unicorn/numeric-separators-style': 'error',
    'unicorn/prefer-add-event-listener': 'error',
    'unicorn/prefer-array-find': 'error',
    'unicorn/prefer-array-flat': 'error',
    'unicorn/prefer-array-flat-map': 'error',
    'unicorn/prefer-array-index-of': 'error',
    'unicorn/prefer-array-some': 'error',
    'unicorn/prefer-at': 'error',
    'unicorn/prefer-code-point': 'error',
    'unicorn/prefer-date-now': 'error',
    'unicorn/prefer-default-parameters': 'error',
    'unicorn/prefer-dom-node-append': 'error',
    'unicorn/prefer-dom-node-dataset': 'error',
    'unicorn/prefer-dom-node-remove': 'error',
    'unicorn/prefer-dom-node-text-content': 'error',
    'unicorn/prefer-export-from': ['error', { ignoreUsedVariables: true }],
    'unicorn/prefer-includes': 'error',
    'unicorn/prefer-json-parse-buffer': 'off',
    'unicorn/prefer-keyboard-event-key': 'error',
    'unicorn/prefer-logical-operator-over-ternary': 'error',
    'unicorn/prefer-math-trunc': 'error',
    'unicorn/prefer-modern-dom-apis': 'error',
    'unicorn/prefer-modern-math-apis': 'error',
    'unicorn/prefer-module': 'error',
    'unicorn/prefer-native-coercion-functions': 'error',
    'unicorn/prefer-negative-index': 'error',
    'unicorn/prefer-node-protocol': 'error',
    'unicorn/prefer-number-properties': 'error',
    'unicorn/prefer-object-from-entries': 'error',
    'unicorn/prefer-optional-catch-binding': 'error',
    'unicorn/prefer-prototype-methods': 'error',
    'unicorn/prefer-query-selector': 'error',
    'unicorn/prefer-reflect-apply': 'error',
    'unicorn/prefer-regexp-test': 'error',
    'unicorn/prefer-set-has': 'error',
    'unicorn/prefer-set-size': 'error',
    'unicorn/prefer-spread': 'error',
    'unicorn/prefer-string-replace-all': 'error',
    'unicorn/prefer-string-slice': 'error',
    'unicorn/prefer-string-starts-ends-with': 'error',
    'unicorn/prefer-string-trim-start-end': 'error',
    'unicorn/prefer-switch': ['error', { minimumCases: 3 }],
    'unicorn/prefer-ternary': 'error',
    'unicorn/prefer-top-level-await': 'off',
    'unicorn/prefer-type-error': 'error',
    'unicorn/relative-url-style': ['error', 'never'],
    'unicorn/require-array-join-separator': 'error',
    'unicorn/require-number-to-fixed-digits-argument': 'error',
    'unicorn/require-post-message-target-origin': 'error',
    'unicorn/string-content': 'off',
    'unicorn/switch-case-braces': ['error', 'always'],
    'unicorn/template-indent': 'error',
    'unicorn/text-encoding-identifier-case': 'error',
    'unicorn/throw-new-error': 'error',

    // ==========================================
    // Security Rules
    // ==========================================
    'security/detect-possible-timing-attacks': 'error',
    'security/detect-unsafe-regex': 'error',
    'security/detect-buffer-noassert': 'error',
    'security/detect-child-process': 'error',
    'security/detect-disable-mustache-escape': 'error',
    'security/detect-eval-with-expression': 'error',
    'security/detect-no-csrf-before-method-override': 'error',
    'security/detect-non-literal-fs-filename': 'error',
    'security/detect-non-literal-regexp': 'error',
    'security/detect-non-literal-require': 'error',
    'security/detect-object-injection': 'warn',
    'security/detect-pseudoRandomBytes': 'error',
    'security/detect-possible-timing-attacks': 'error',

    // ==========================================
    // Optimize Regex Rules
    // ==========================================
    'optimize-regex/optimize-regex': 'warn',

    // ==========================================
    // No Secrets Rules
    // ==========================================
    'no-secrets/no-secrets': [
      'error',
      {
        tolerance: 4.5,
        ignoreContent: ['example.com', 'test', 'localhost', 'example', 'sample'],
        ignoreModules: true,
      },
    ],

    // ==========================================
    // Chai-Friendly Rules
    // ==========================================
    'chai-friendly/no-unused-expressions': 'error',

    // ==========================================
    // Vitest Rules
    // ==========================================
    'vitest/consistent-test-it': ['error', { fn: 'it', withinDescribe: 'it' }],
    'vitest/expect-expect': 'error',
    'vitest/max-expects': ['error', { max: 5 }],
    'vitest/no-conditional-expect': 'error',
    'vitest/no-conditional-tests': 'error',
    'vitest/no-disabled-tests': 'warn',
    'vitest/no-done-callback': 'error',
    'vitest/no-focused-tests': 'error',
    'vitest/no-identical-title': 'error',
    'vitest/no-standalone-expect': 'error',
    'vitest/no-test-prefixes': 'error',
    'vitest/prefer-called-with': 'error',
    'vitest/prefer-expect-assertions': 'off',
    'vitest/prefer-hooks-on-top': 'error',
    'vitest/prefer-lowercase-title': ['error', { ignore: ['describe'] }],
    'vitest/prefer-spy-on': 'error',
    'vitest/prefer-to-be': 'error',
    'vitest/prefer-to-contain': 'error',
    'vitest/prefer-to-have-length': 'error',
    'vitest/require-hook': 'error',
    'vitest/require-to-throw-message': 'error',
    'vitest/require-top-level-describe': 'error',
    'vitest/valid-describe-callback': 'error',
    'vitest/valid-expect': 'error',
    'vitest/valid-title': 'error',

    // ==========================================
    // Overrides for specific files
    // ==========================================
    overrides: [
      // Configuration files
      {
        files: ['*.config.{js,ts}', '.eslintrc.{js,cjs}', 'vite.config.{js,ts}'],
        rules: {
          'import/no-extraneous-dependencies': 'off',
          'unicorn/prefer-module': 'off',
          '@typescript-eslint/no-var-requires': 'off',
          'no-console': 'off',
          'sonarjs/no-duplicate-string': 'off',
        },
      },
      
      // Test files
      {
        files: [
          '**/*.test.{ts,tsx}',
          '**/*.spec.{ts,tsx}',
          '**/__tests__/**/*.{ts,tsx}',
          '**/tests/**/*.{ts,tsx}',
        ],
        rules: {
          '@typescript-eslint/no-explicit-any': 'off',
          '@typescript-eslint/no-non-null-assertion': 'off',
          'import/no-extraneous-dependencies': 'off',
          'max-lines-per-function': 'off',
          'sonarjs/no-duplicate-string': 'off',
          'unicorn/consistent-function-scoping': 'off',
          'unicorn/no-null': 'off',
          'no-secrets/no-secrets': 'off',
        },
      },
      
      // Cypress tests
      {
        files: ['cypress/**/*.{js,ts}', '**/*.cy.{js,ts,jsx,tsx}'],
        rules: {
          'jest/valid-expect': 'off',
          '@typescript-eslint/no-namespace': 'off',
          'no-unused-expressions': 'off',
          'chai-friendly/no-unused-expressions': 'off',
        },
      },
      
      // Storybook files
      {
        files: ['**/*.stories.{ts,tsx}'],
        rules: {
          'import/no-anonymous-default-export': 'off',
          'react/jsx-props-no-spreading': 'off',
          'max-lines-per-function': 'off',
        },
      },
      
      // API mocks
      {
        files: ['**/mocks/**/*.{ts,js}', '**/*.mock.{ts,js}'],
        rules: {
          'max-lines': 'off',
          'sonarjs/no-duplicate-string': 'off',
          '@typescript-eslint/no-explicit-any': 'off',
        },
      },
      
      // TypeScript declaration files
      {
        files: ['**/*.d.ts'],
        rules: {
          '@typescript-eslint/no-unused-vars': 'off',
          '@typescript-eslint/triple-slash-reference': 'off',
          'spaced-comment': 'off',
        },
      },
    ],
  },

  // ==========================================
  // Global Variables
  // ==========================================
  globals: {
    React: 'readonly',
    JSX: 'readonly',
    NodeJS: 'readonly',
    cy: 'readonly',
    Cypress: 'readonly',
    expect: 'readonly',
    assert: 'readonly',
    vitest: 'readonly',
    vi: 'readonly',
    describe: 'readonly',
    it: 'readonly',
    before: 'readonly',
    after: 'readonly',
    beforeEach: 'readonly',
    afterEach: 'readonly',
  },

  // ==========================================
  // Ignore Patterns
  // ==========================================
  ignorePatterns: [
    'dist',
    'build',
    'coverage',
    'node_modules',
    '*.min.js',
    '*.bundle.js',
    '*.config.js',
    '!.eslintrc.js',
    '!.prettierrc',
    'public',
    'static',
    'cypress/videos',
    'cypress/screenshots',
    '**/vendor/**',
  ],
};