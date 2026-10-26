import assert from 'node:assert/strict'
import { afterEach, beforeEach, test } from 'node:test'

import { createPinia, setActivePinia } from 'pinia'

import request from '../src/api/request.ts'
import { registerProjectResolver } from './support/project-resolver.ts'

registerProjectResolver()

// 静态 import 会被提升到 registerHooks 之前，所以业务模块必须动态引入
const { useInterviewStore } = await import('../src/stores/interview.store.ts')

type Store = ReturnType<typeof useInterviewStore>

interface SseHarness {
  response: Response
  push: (text: string) => void
  close: () => void
}

const encoder = new TextEncoder()

const createSseHarness = (status = 200): SseHarness => {
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const stream = new ReadableStream<Uint8Array>({
    start(inner) {
      controller = inner
    },
  })
  return {
    response: new Response(stream, {
      status,
      headers: { 'Content-Type': 'text/event-stream' },
    }),
    push: (text) => controller.enqueue(encoder.encode(text)),
    close: () => controller.close(),
  }
}

const doneFrame = (payload: Record<string, unknown>) =>
  `event: done\ndata: ${JSON.stringify(payload)}\n\n`

const deltaFrame = (text: string) => `event: delta\ndata: ${JSON.stringify({ text })}\n\n`

const stageFrame = (label: string) =>
  `event: stage\ndata: ${JSON.stringify({ stage: 'generating', label })}\n\n`

const waitFor = async (predicate: () => boolean, timeout = 2000) => {
  const startedAt = Date.now()
  while (!predicate()) {
    if (Date.now() - startedAt > timeout) throw new Error('等待状态超时')
    await new Promise((resolve) => setTimeout(resolve, 5))
  }
}

const originalFetch = globalThis.fetch
let syncCalls = 0
let syncPayload: Record<string, unknown> = {}
let syncError: Error | null = null
let fetchCalls = 0
let lastFetchInit: RequestInit | undefined

const resetStore = (): Store => {
  setActivePinia(createPinia())
  const store = useInterviewStore()
  store.info.sessionId = 's1'
  store.info.currentQuestionNo = 1
  store.info.status = 'in_progress'
  return store
}

const aiMessages = (store: Store) => store.messages.filter((item) => item.role === 'ai')

beforeEach(() => {
  syncCalls = 0
  fetchCalls = 0
  syncError = null
  lastFetchInit = undefined
  syncPayload = {
    session_id: 's1',
    round_no: 2,
    next_question: '降级后的题目：说说你的项目',
    is_finished: false,
    decision: 'continue',
  }
  request.defaults.adapter = async (config) => {
    syncCalls += 1
    if (syncError) throw syncError
    return {
      data: syncPayload,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }
  }
})

afterEach(() => {
  globalThis.fetch = originalFetch
})

test('流式成功：stage 更新提示、delta 逐字追加、done 收尾', async () => {
  const store = resetStore()
  const sse = createSseHarness()
  globalThis.fetch = async (_input, init) => {
    fetchCalls += 1
    lastFetchInit = init
    return sse.response
  }

  const promise = store.submitAnswer('我叫张三，做过支付系统')

  sse.push(stageFrame('正在生成问题'))
  await waitFor(() => store.stageLabel === '正在生成问题')
  assert.equal(store.generating, true)

  const firstDelta = '那你'
  sse.push(deltaFrame(firstDelta))
  await waitFor(() => aiMessages(store).some((item) => item.content === firstDelta))
  assert.equal(store.isStreaming, true)

  const secondDelta = '介绍一下你负责的支付模块'
  sse.push(deltaFrame(secondDelta))
  await waitFor(() => store.messages.some((item) => item.content === firstDelta + secondDelta))

  sse.push(
    doneFrame({
      session_id: 's1',
      round_no: 2,
      next_question: firstDelta + secondDelta,
      is_finished: false,
      decision: 'continue',
    }),
  )
  await promise

  const messages = aiMessages(store)
  assert.equal(messages.length, 2, '只有首题 + 这一条流式题，不应重复插入')
  assert.equal(messages[1].content, firstDelta + secondDelta)
  assert.equal(messages[1].questionNo, 2)
  assert.equal(messages[1].streaming, false)
  assert.equal(store.info.currentQuestionNo, 2)
  assert.equal(store.isStreaming, false)
  assert.equal(store.generating, false)
  assert.equal(store.loading, false)
  assert.equal(store.stageLabel, '')
  assert.equal(syncCalls, 0, '流式成功不该再打同步接口')

  assert.equal(fetchCalls, 1)
  assert.ok(String(lastFetchInit?.method).toUpperCase() === 'POST')
  assert.equal(lastFetchInit?.body, JSON.stringify({ answer: '我叫张三，做过支付系统' }))
})

test('done 的 next_question 为准：重复题兜底不会把两道题粘在一起', async () => {
  const store = resetStore()
  const sse = createSseHarness()
  globalThis.fetch = async () => sse.response

  const promise = store.submitAnswer('回答')

  sse.push(deltaFrame('旧题：介绍一下你的项目'))
  await waitFor(() => store.messages.some((item) => item.content === '旧题：介绍一下你的项目'))
  sse.push(deltaFrame('新题：聊聊 JVM 内存模型'))
  await waitFor(() => store.messages.some((item) => item.content.includes('JVM')))

  sse.push(
    doneFrame({
      session_id: 's1',
      round_no: 2,
      next_question: '新题：聊聊 JVM 内存模型',
      is_finished: false,
      decision: 'switch',
    }),
  )
  await promise

  const messages = aiMessages(store)
  assert.equal(messages.length, 2)
  assert.equal(messages[1].content, '新题：聊聊 JVM 内存模型')
  assert.equal(syncCalls, 0)
})

test('SSE 非 2xx：丢弃半截气泡并回落同步接口', async () => {
  const store = resetStore()
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: 'Not Found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    })

  await store.submitAnswer('回答')

  assert.equal(syncCalls, 1, '同步接口只重试一次')
  const messages = aiMessages(store)
  assert.equal(messages.length, 2)
  assert.equal(messages[1].content, '降级后的题目：说说你的项目')
  assert.equal(messages[1].questionNo, 2)
  assert.equal(store.generating, false)
  assert.equal(store.isStreaming, false)
  assert.equal(store.errorMessage, '')
})

test('流内 error 事件：半截气泡被丢弃，降级后只留一条完整题目', async () => {
  const store = resetStore()
  const sse = createSseHarness()
  globalThis.fetch = async () => sse.response

  const promise = store.submitAnswer('回答')

  sse.push(deltaFrame('半截题'))
  await waitFor(() => store.messages.some((item) => item.content === '半截题'))
  sse.push('event: error\ndata: {"detail":"LLM provider error: timeout"}\n\n')
  sse.close()

  await promise

  assert.equal(syncCalls, 1)
  const messages = aiMessages(store)
  assert.equal(messages.length, 2, '半截气泡必须被移除')
  assert.equal(messages[1].content, '降级后的题目：说说你的项目')
  assert.equal(messages.some((item) => item.content === '半截题'), false)
})

test('流没有 done 就结束：按中断处理并回落同步接口', async () => {
  const store = resetStore()
  const sse = createSseHarness()
  globalThis.fetch = async () => sse.response

  const promise = store.submitAnswer('回答')
  sse.push(stageFrame('正在生成问题'))
  sse.push(deltaFrame('只出到一半'))
  await waitFor(() => store.messages.some((item) => item.content === '只出到一半'))
  sse.close()

  await promise

  assert.equal(syncCalls, 1)
  assert.equal(aiMessages(store).length, 2)
  assert.equal(store.messages.some((item) => item.content === '只出到一半'), false)
})

test('流式和同步都失败：回填 failedDraft 并回滚这条回答', async () => {
  const store = resetStore()
  globalThis.fetch = async () => new Response('boom', { status: 502 })
  syncError = Object.assign(new Error('Request failed with status code 500'), {
    isAxiosError: true,
    response: { status: 500, statusText: 'Internal Server Error', headers: {}, data: { detail: '同步接口也挂了' } },
  })

  await assert.rejects(store.submitAnswer(' 这段回答不能丢 '))

  assert.equal(syncCalls, 1)
  assert.equal(store.failedDraft, '这段回答不能丢')
  assert.equal(store.errorMessage, '同步接口也挂了')
  assert.equal(store.messages.length, 1, '用户消息应被回滚')
  assert.equal(store.answeredQuestions.length, 0)
  assert.equal(store.loading, false)
  assert.equal(store.generating, false)
})

test('结束面试中途 abort：不降级、不报错，半截气泡清掉', async () => {
  const store = resetStore()
  let aborted = false
  globalThis.fetch = async (_input, init) => {
    const signal = init?.signal
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(stageFrame('正在生成问题')))
        signal?.addEventListener('abort', () => {
          aborted = true
          controller.error(new DOMException('Aborted', 'AbortError'))
        })
      },
    })
    return new Response(stream, { status: 200 })
  }

  const promise = store.submitAnswer('回答到一半')
  await waitFor(() => store.stageLabel === '正在生成问题')

  store.cancelStream()
  await promise

  assert.equal(aborted, true, '应该真的 abort 掉流')
  assert.equal(syncCalls, 0)
  assert.equal(store.failedDraft, '')
  assert.equal(store.errorMessage, '')
  // 用户这条回答留在原地，但不能再冒出半截 AI 题目
  assert.equal(store.messages.length, 2)
  assert.equal(aiMessages(store).length, 1)
  assert.equal(store.isStreaming, false)
  assert.equal(store.generating, false)
  assert.equal(store.loading, false)
})

test('done 直接结束面试：标记 finished 并发结束语', async () => {
  const store = resetStore()
  const sse = createSseHarness()
  globalThis.fetch = async () => sse.response

  const promise = store.submitAnswer('最后一题的回答')
  await waitFor(() => store.generating)
  sse.push(
    doneFrame({
      session_id: 's1',
      round_no: 1,
      next_question: null,
      is_finished: true,
      decision: 'end',
    }),
  )
  await promise

  assert.equal(store.info.status, 'finished')
  assert.equal(store.isStreaming, false)
  assert.equal(store.generating, false)
  assert.ok(store.messages.some((item) => item.content.includes('本次模拟面试已经结束')))
  assert.equal(aiMessages(store).some((item) => item.streaming), false)
})
