<script setup>
// 1. 导入语句
import { computed, onMounted, ref } from 'vue'

import { useRouter } from 'vue-router'

import {
  acceptAgreement,
  isAgreementAccepted,
  revokeAgreement,
} from '../utils/agreement.js'

// 2. Props — 无
// 3. Emits — 无

// 4. 组合式函数
const router = useRouter()

// 5. 响应式数据
const isAccepted = ref(false)
const hasScrolledToBottom = ref(false)
const isAgreeCheckboxChecked = ref(false)
const acceptedAt = ref('')

// 6. 计算属性
const canAccept = computed(
  () => hasScrolledToBottom.value && isAgreeCheckboxChecked.value,
)

// 7. 方法
function loadAcceptanceState() {
  isAccepted.value = isAgreementAccepted()
  try {
    const raw = localStorage.getItem('user_agreement_accepted_v1')
    if (raw) {
      const parsed = JSON.parse(raw)
      acceptedAt.value = typeof parsed?.at === 'string' ? parsed.at : ''
    } else {
      acceptedAt.value = ''
    }
  } catch {
    acceptedAt.value = ''
  }
}

function handleScrollToBottom() {
  if (!hasScrolledToBottom.value) {
    hasScrolledToBottom.value = true
  }
}

function handleAccept() {
  if (!canAccept.value) {
    return
  }
  const now = acceptAgreement()
  isAccepted.value = true
  acceptedAt.value = now
  // 接受后尝试跳转回原请求路径
  const route = router.currentRoute.value
  const redirect = typeof route.query?.redirect === 'string' ? route.query.redirect : ''
  if (redirect) {
    router.replace(redirect)
  }
}

function handleRevoke() {
  revokeAgreement()
  isAccepted.value = false
  acceptedAt.value = ''
  hasScrolledToBottom.value = false
  isAgreeCheckboxChecked.value = false
}

function handleBack() {
  if (router && typeof router.back === 'function') {
    router.back()
  }
}

// 8. 生命周期
onMounted(() => {
  loadAcceptanceState()
})
</script>

<template>
  <div class="agreement-page">
    <div class="agreement-container">
      <header class="agreement-header">
        <h1 class="agreement-title">用户协议与隐私政策</h1>
        <p class="agreement-subtitle">
          请仔细阅读以下全部条款。接受本协议后，您方可使用本系统的核心分析功能。
        </p>
        <div v-if="isAccepted" class="agreement-status accepted">
          <span class="status-icon">✓</span>
          <span class="status-text">
            您已于 <strong>{{ acceptedAt }}</strong> 接受本协议
          </span>
          <button
            class="link-btn"
            type="button"
            @click="handleRevoke"
          >
            撤回接受
          </button>
        </div>
      </header>

      <article
        class="agreement-content"
        @scroll="handleScrollToBottom"
      >
        <section class="agreement-section">
          <h2 class="section-title">一、系统定位说明</h2>
          <p>
            本系统全称为"帮信罪主观明知智能分析系统"（以下简称"本系统"），
            是一款基于大语言模型（LLM）面向司法办案场景的<strong>辅助参考工具</strong>。
          </p>
          <p>
            本系统<strong>不</strong>替代办案人员的专业判断、<strong>不</strong>构成法律意见、
            <strong>不</strong>作为定罪量刑的最终依据。所有分析结果仅供具备相应资质的
            司法工作人员在人工审查的基础上参考使用。
          </p>
        </section>

        <section class="agreement-section">
          <h2 class="section-title">二、用户数据使用政策</h2>
          <p>
            本系统在为您提供服务的过程中，会处理以下类型的数据：
          </p>
          <ul>
            <li>案件事实文本、案件描述、用户输入的查询内容；</li>
            <li>分析结果、知识条目、报告导出记录；</li>
            <li>登录凭证（经哈希存储）、操作日志、访问 IP 地址；</li>
            <li>用于性能与安全审计的元数据（不含敏感个人信息）。</li>
          </ul>
          <p>
            上述数据<strong>仅</strong>用于为您提供分析服务、系统优化与安全审计，
            <strong>不会</strong>被用于训练第三方模型或对外共享。如需删除您提交的数据，
            请通过本协议末尾的官方联系方式提交申请。
          </p>
        </section>

        <section class="agreement-section">
          <h2 class="section-title">三、AI 功能局限性声明</h2>
          <p>
            本系统采用大语言模型对案件事实进行多维度智能分析。受限于模型的训练数据、
            上下文窗口与生成机制，分析结果<strong>可能存在</strong>以下情况：
          </p>
          <ul>
            <li>对事实细节的<strong>遗漏、误读或编造</strong>（即"幻觉"）；</li>
            <li>对法条与司法解释的<strong>引用错误或过期</strong>；</li>
            <li>在边缘案件或新型犯罪形态下给出<strong>过于笼统或不准确</strong>的结论；</li>
            <li>对主观意图的推断<strong>存在偏差</strong>，无法替代专业人员的实质审查。</li>
          </ul>
          <p>
            因此，<strong>所有 AI 生成内容必须经具备相应资质的司法工作人员人工审查后</strong>
            方可作为参考；本系统不对因直接采信 AI 分析结果而产生的任何后果承担责任。
          </p>
        </section>

        <section class="agreement-section">
          <h2 class="section-title">四、责任界定条款</h2>
          <p>使用本系统即表示您同意以下责任界定：</p>
          <ul>
            <li>
              <strong>用户责任：</strong>用户应保证提交内容的合法性，对自身账户下发生的所有操作负责；
            </li>
            <li>
              <strong>系统责任：</strong>本系统仅在法律法规允许的范围内提供辅助分析服务，
              不对 AI 分析结果的准确性、完整性、时效性承担保证责任；
            </li>
            <li>
              <strong>免责情形：</strong>因不可抗力、第三方服务故障、网络中断、用户违规操作
              等原因造成的服务中断或数据损失，本系统不承担赔偿责任；
            </li>
            <li>
              <strong>争议解决：</strong>因本协议引发的争议，适用中华人民共和国法律，
              协商不成的，提交本系统运营方所在地有管辖权的人民法院解决。
            </li>
          </ul>
        </section>

        <section class="agreement-section">
          <h2 class="section-title">五、知识产权说明</h2>
          <p>
            本系统的软件代码、UI 设计、品牌标识、文档资料、提示词工程方案及知识库内容，
            其著作权、商标权及其他知识产权<strong>均归本系统运营方所有</strong>，
            未经书面授权，任何单位或个人不得以任何形式复制、修改、传播或用于商业目的。
          </p>
          <p>
            用户在本系统内<strong>自主输入</strong>的案件事实、备注等内容，
            其知识产权仍归用户所有；本系统仅在为您提供服务的必要范围内进行存储与处理。
          </p>
        </section>

        <section class="agreement-section">
          <h2 class="section-title">六、官方联系方式信息</h2>
          <p>如您对本协议、隐私政策或本系统的使用有任何疑问、建议或投诉，请通过以下方式联系我们：</p>
          <ul class="contact-list">
            <li><strong>联系邮箱：</strong>support@legal-analysis.example.com</li>
            <li><strong>反馈地址：</strong>https://legal-analysis.example.com/feedback</li>
            <li><strong>办公地址：</strong>北京市海淀区中关村南大街 X 号</li>
            <li><strong>客服电话：</strong>010-0000-0000（工作日 9:00-18:00）</li>
          </ul>
        </section>

        <div class="agreement-footer-hint">
          协议正文结束。请向下滚动至底部后，方可勾选"我已阅读并同意"并点击"接受协议"。
        </div>
      </article>

      <footer class="agreement-footer">
        <label class="agree-checkbox">
          <input
            v-model="isAgreeCheckboxChecked"
            type="checkbox"
            :disabled="!hasScrolledToBottom || isAccepted"
          />
          <span>我已完整阅读并理解以上全部条款，自愿作出接受的意思表示。</span>
        </label>
        <div class="action-row">
          <button
            class="btn btn-secondary"
            type="button"
            @click="handleBack"
          >
            返回
          </button>
          <button
            v-if="!isAccepted"
            class="btn btn-primary"
            type="button"
            :disabled="!canAccept"
            @click="handleAccept"
          >
            接受协议
          </button>
          <span v-else class="accepted-hint">您已接受本协议，可使用系统全部功能。</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.agreement-page {
  min-height: 100vh;
  padding: 2rem 1rem;
  background: linear-gradient(135deg, #eef2ff 0%, #f5f7fa 100%);
}

.agreement-container {
  max-width: 880px;
  margin: 0 auto;
  background: #ffffff;
  border-radius: var(--border-radius-lg, 12px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.agreement-header {
  padding: 2rem 2rem 1.25rem;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
}

.agreement-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin: 0 0 0.5rem;
}

.agreement-subtitle {
  font-size: 0.95rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
}

.agreement-status {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #ecfdf5;
  border: 1px solid #6ee7b7;
  border-radius: var(--border-radius, 8px);
  color: #065f46;
  font-size: 0.9rem;
}

.status-icon {
  font-size: 1.1rem;
}

.status-text {
  flex: 1;
}

.link-btn {
  background: none;
  border: none;
  color: #4f46e5;
  font-size: 0.85rem;
  cursor: pointer;
  text-decoration: underline;
  padding: 0.25rem 0.5rem;
}

.link-btn:hover {
  color: #4338ca;
}

.agreement-content {
  max-height: 60vh;
  overflow-y: auto;
  padding: 1.5rem 2rem;
  font-size: 0.95rem;
  line-height: 1.8;
  color: var(--text-primary, #1e293b);
}

.agreement-section {
  margin-bottom: 1.75rem;
}

.agreement-section:last-of-type {
  margin-bottom: 1rem;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-primary, #4f46e5);
  margin: 0 0 0.75rem;
}

.agreement-section p {
  margin: 0 0 0.75rem;
}

.agreement-section ul {
  padding-left: 1.5rem;
  margin: 0 0 0.75rem;
}

.agreement-section li {
  margin-bottom: 0.4rem;
}

.contact-list {
  list-style: none;
  padding-left: 0;
}

.contact-list li {
  margin-bottom: 0.4rem;
}

.agreement-footer-hint {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #fef3c7;
  border-left: 4px solid #eab308;
  border-radius: var(--border-radius, 8px);
  color: #78350f;
  font-size: 0.85rem;
}

.agreement-footer {
  padding: 1.25rem 2rem 1.75rem;
  border-top: 1px solid var(--border-color, #e2e8f0);
  background: var(--bg-secondary, #f8fafc);
}

.agree-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-primary, #1e293b);
  cursor: pointer;
  margin-bottom: 1rem;
}

.agree-checkbox input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.agree-checkbox input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.accepted-hint {
  color: var(--color-success, #16a34a);
  font-size: 0.9rem;
  font-weight: 500;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.6rem 1.4rem;
  font-size: 0.95rem;
  font-weight: 500;
  border: none;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: all 150ms ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary, #4f46e5);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #4338ca;
}

.btn-secondary {
  background: transparent;
  color: var(--text-secondary, #64748b);
  border: 1px solid var(--border-color, #e2e8f0);
}

.btn-secondary:hover {
  background: var(--bg-tertiary, #f1f5f9);
}

@media (max-width: 640px) {
  .agreement-header,
  .agreement-content,
  .agreement-footer {
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }

  .agreement-title {
    font-size: 1.4rem;
  }
}
</style>
