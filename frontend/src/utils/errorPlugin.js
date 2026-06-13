import * as Sentry from '@sentry/vue'

import { collectContext, logError, LogLevel } from './errorHandler.js'

const DEV = import.meta.env.DEV
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
const SENTRY_ENABLED = Boolean(SENTRY_DSN && SENTRY_DSN.trim())

function setupGlobalErrorHandler(app) {
  app.config.errorHandler = (err, vm, info) => {
    const context = collectContext(err)
    context.vueInfo = info
    context.componentName = vm?.$options?.name || vm?.$options?._componentTag || 'anonymous'

    logError(LogLevel.ERROR, `[Vue Error] ${info}`, context)

    if (SENTRY_ENABLED) {
      Sentry.withScope((scope) => {
        scope.setTag('feature', 'vue_error')
        scope.setExtra('vueInfo', info)
        scope.setExtra('componentName', context.componentName)
        Sentry.captureException(err)
      })
    }

    if (DEV) {
      console.error('发生错误的组件:', context.componentName)
    }
  }
}

function setupUnhandledRejection() {
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason
    const context = collectContext(error)
    context.rejectionType = 'unhandled'

    logError(LogLevel.ERROR, '[Unhandled Rejection]', context)

    if (SENTRY_ENABLED) {
      Sentry.captureException(error, {
        tags: { feature: 'unhandled_rejection' },
      })
    }

    if (!DEV) {
      event.preventDefault()
    }
  })
}

function setupResourceErrorCapture() {
  window.addEventListener(
    'error',
    (event) => {
      if (event.target && (event.target.tagName === 'IMG' || event.target.tagName === 'SCRIPT' || event.target.tagName === 'LINK')) {
        const context = {
          timestamp: new Date().toISOString(),
          resourceUrl: event.target.src || event.target.href,
          resourceTag: event.target.tagName,
        }
        logError(LogLevel.WARN, `[Resource Load Error] ${context.resourceTag}`, context)

        if (SENTRY_ENABLED) {
          Sentry.addBreadcrumb({
            category: 'resource',
            level: 'warning',
            data: context,
          })
        }
      }
    },
    true
  )
}

export default {
  install(app) {
    setupGlobalErrorHandler(app)
    setupUnhandledRejection()
    setupResourceErrorCapture()
  },
}
