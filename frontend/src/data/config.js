// 案件事实输入模板
export const caseInputTemplate = `请在此处输入案件事实...

示例格式：
嫌疑人XXX在交易过程中，通过微信/聊天与买家沟通过程中...
（请详细描述交易过程、聊天内容、嫌疑人行为等关键信息）`

// 维度名称映射
export const dimensionNames = {
  abnormal_transaction: '交易异常性',
  communication_content: '沟通内容',
  suspect_behavior: '嫌疑人行为',
}

// 维度描述
export const dimensionDescriptions = {
  abnormal_transaction: '分析交易价格、方式、频率等是否明显偏离正常市场行为',
  communication_content: '分析聊天记录、暗语、暗示性表述等是否反映主观认知',
  suspect_behavior: '分析嫌疑人是否采取规避侦查措施及行为合理性',
}

// 结论类型颜色配置
export const conclusionColors = {
  明显明知: {
    bg: '#dcfce7',
    text: '#166534',
    border: '#4ade80',
    icon: '✓',
  },
  确实不明知: {
    bg: '#dbeafe',
    text: '#1e40af',
    border: '#60a5fa',
    icon: '✗',
  },
  边缘情况: {
    bg: '#fef3c7',
    text: '#92400e',
    border: '#fbbf24',
    icon: '?',
  },
}
