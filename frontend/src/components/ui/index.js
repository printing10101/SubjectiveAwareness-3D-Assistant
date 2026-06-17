/**
 * ============================================================================
 * index.js - index 功能模块
 * ============================================================================
 *
 * @file index.js
 * @description 帮信罪主观明知智能分析系统 - index 功能模块
 * @version 1.0.0
 * @author 帮信罪智能分析系统开发团队
 * @copyright 2024-2026 帮信罪智能分析系统
 *
 * 功能说明：
 *   - 核心功能实现、业务逻辑处理、系统集成
 *   - 数据状态管理和同步
 *   - 业务逻辑封装和复用
 *   - 错误处理和异常恢复
 *
 * 技术栈：
 *   - JavaScript / TypeScript
 *   - Pinia 状态管理（适用于 Store）
 *   - Axios HTTP 客户端（适用于 API）
 *   - Vue Router（适用于 Router）
 *
 * 使用说明：
 *   - 导入方式：// 导入依赖模块
import { index } from 'frontend/src/components/ui/index.js'
 *   - 依赖注入：通过 Vue 的 provide/inject 或 Pinia
 *   - 错误处理：统一的错误捕获和日志记录
 *
 * ============================================================================
 */

/**
 * index.js - 路由配置模块，定义应用路由表、导航守卫和权限控制逻辑
 *
 * @module index.js
 * @description 帮信罪主观明知智能分析系统 - 前端路由配置模块，定义应用路由表、导航守卫和权限控制逻辑
 * @version 1.0.0
 */

/**
 * UI 组件统一导出
 */
// 导出模块默认接口，供其他模块引用
// 导出模块接口
export { default as BaseButton } from './BaseButton.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseInput } from './BaseInput.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseSelect } from './BaseSelect.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseTable } from './BaseTable.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseCard } from './BaseCard.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseModal } from './BaseModal.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseTabs } from './BaseTabs.vue'
// 导出模块默认接口，供其他模块引用
export { default as BasePagination } from './BasePagination.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseBadge } from './BaseBadge.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseDivider } from './BaseDivider.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseEmpty } from './BaseEmpty.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseLoading } from './BaseLoading.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseSkeleton } from './BaseSkeleton.vue'
// 导出模块默认接口，供其他模块引用
export { default as BaseToast } from './BaseToast.vue'
// 导出模块默认接口，供其他模块引用
export { default as ResponsiveImage } from './ResponsiveImage.vue'
