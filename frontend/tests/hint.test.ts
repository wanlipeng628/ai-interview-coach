import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  ANSWER_HINT,
  GENERATING_LONG_THRESHOLD,
  resolveInterviewHint,
  SUBMIT_FAILED_HINT,
} from '../src/utils/interviewHint.ts'

const waiting = { generating: true, isStreaming: false, elapsedSeconds: 0, errorMessage: '' }

test('点击发送后立刻显示思考文案（不用等 stage 事件）', () => {
  assert.equal(resolveInterviewHint(waiting), '面试官正在思考下一题…')
})

test('首个 delta 到达后立刻切回答题建议', () => {
  assert.equal(
    resolveInterviewHint({ ...waiting, isStreaming: true, elapsedSeconds: 1 }),
    ANSWER_HINT,
  )
})

test('满 8 秒仍没等到 delta 才切斟酌文案', () => {
  assert.equal(
    resolveInterviewHint({ ...waiting, elapsedSeconds: GENERATING_LONG_THRESHOLD - 1 }),
    '面试官正在思考下一题…',
  )
  assert.equal(
    resolveInterviewHint({ ...waiting, elapsedSeconds: GENERATING_LONG_THRESHOLD }),
    '面试官还在斟酌题目，请稍候…',
  )
})

test('已经开始输出时压过 8 秒档：再慢也显示答题建议', () => {
  assert.equal(
    resolveInterviewHint({ ...waiting, isStreaming: true, elapsedSeconds: 30 }),
    ANSWER_HINT,
  )
})

test('慢路径文案不提「服务繁忙」也不提「重试」', () => {
  const slow = resolveInterviewHint({ ...waiting, elapsedSeconds: GENERATING_LONG_THRESHOLD })
  assert.ok(!/繁忙|重试/.test(slow), `慢路径文案不应误导：${slow}`)
})

test('失败文案保持不变', () => {
  assert.equal(
    resolveInterviewHint({ ...waiting, generating: false, errorMessage: '网络连接失败' }),
    SUBMIT_FAILED_HINT,
  )
})

test('空闲状态显示答题建议', () => {
  assert.equal(resolveInterviewHint({ ...waiting, generating: false }), ANSWER_HINT)
})
