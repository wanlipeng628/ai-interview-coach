/**
 * 面试官出题等待期的 hint 口径（AIC-75 定口径 / AIC-76 落地）。
 *
 * 文案由前端自己按状态机管控，不再消费后端 stage 事件的 label——那一档只有
 * 「正在生成问题」，信息密度不如按时间和 delta 分层。
 */

/** 题目已经开始往外流、以及空闲待答时的提示 */
export const ANSWER_HINT = '建议：背景 · 方案 · 结果 · 反思'

/** AIC-71 的失败提示：回答已回填输入框，可以重发 */
export const SUBMIT_FAILED_HINT = '上次提交失败，回答已保留，可重新发送'

/** 生成超过这个秒数还没收到第一个 delta，就提示面试官在斟酌 */
export const GENERATING_LONG_THRESHOLD = 8

export interface InterviewHintState {
  /** 已提交、后端还在出题 */
  generating: boolean
  /** 已经收到第一个 delta，题目正在逐字出现 */
  isStreaming: boolean
  /** generating 开始后经过的秒数 */
  elapsedSeconds: number
  /** 上一次提交的失败提示 */
  errorMessage: string
}

/**
 * 等待期 hint 的优先级：失败 > 生成中·输出 > 生成中·等待偏久 > 生成中·初始 > 空闲。
 */
export function resolveInterviewHint(state: InterviewHintState): string {
  if (state.generating) {
    // 题目已经在流了，用户看得到进展，这时候给答题提示比继续报等待更有价值
    if (state.isStreaming) return ANSWER_HINT
    // 慢路径是模型在斟酌题目，不是服务繁忙，所以不承诺「自动重试」
    if (state.elapsedSeconds >= GENERATING_LONG_THRESHOLD) return '面试官还在斟酌题目，请稍候…'
    return '面试官正在思考下一题…'
  }
  if (state.errorMessage) return SUBMIT_FAILED_HINT
  return ANSWER_HINT
}
