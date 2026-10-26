import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import type { Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { after, before, test } from 'node:test'

import { registerProjectResolver } from './support/project-resolver.ts'

registerProjectResolver()

const api = await import('../src/api/interview.api.ts')

const nativeFetch = globalThis.fetch
const encoder = new TextEncoder()
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

let server: Server
let origin = ''

const sseHeaders = {
  'Content-Type': 'text/event-stream',
  'Cache-Control': 'no-cache',
  Connection: 'keep-alive',
}

/** 真实 HTTP 流：每个 write 是一个 chunk，用来验证 fetch + 分片解析确实能拼回事件 */
const writeSlowly = async (response: import('node:http').ServerResponse, chunk: string | Uint8Array) => {
  response.write(chunk)
  await sleep(5)
}

before(async () => {
  server = createServer((request, response) => {
    const url = request.url ?? ''

    if (url.includes('/interview/happy/answer/stream')) {
      response.writeHead(200, sseHeaders)
      void (async () => {
        await writeSlowly(response, 'event: stage\ndata: {"stage":"generating","label":"正在生成问题"}\n\n')
        await writeSlowly(response, 'event: delta\ndata: {"text":"那你"}\n\n')
        // 把一个汉字切成两半，跨 chunk 传
        const bytes = encoder.encode('event: delta\ndata: {"text":"介绍一下支付模块"}\n\n')
        const cut = bytes.findIndex((byte) => byte > 0x7f) + 1
        await writeSlowly(response, bytes.slice(0, cut))
        await writeSlowly(response, bytes.slice(cut))
        await writeSlowly(
          response,
          `event: done\ndata: ${JSON.stringify({
            session_id: 'happy',
            round_no: 2,
            next_question: '那你介绍一下支付模块',
            is_finished: false,
            decision: 'continue',
          })}\n\n`,
        )
        response.end()
      })()
      return
    }

    if (url.includes('/interview/error-event/answer/stream')) {
      response.writeHead(200, sseHeaders)
      void (async () => {
        await writeSlowly(response, 'event: delta\ndata: {"text":"半截题"}\n\n')
        await writeSlowly(response, 'event: error\ndata: {"detail":"LLM provider error: timeout"}\n\n')
        response.end()
      })()
      return
    }

    if (url.includes('/interview/no-done/answer/stream')) {
      response.writeHead(200, sseHeaders)
      void (async () => {
        await writeSlowly(response, 'event: stage\ndata: {"stage":"generating","label":"正在生成问题"}\n\n')
        await writeSlowly(response, 'event: delta\ndata: {"text":"只出到一半"}\n\n')
        response.end()
      })()
      return
    }

    if (url.includes('/interview/abort/answer/stream')) {
      response.writeHead(200, sseHeaders)
      response.write('event: stage\ndata: {"stage":"generating","label":"正在生成问题"}\n\n')
      // 之后一直挂着，等客户端 abort
      return
    }

    response.writeHead(404, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ detail: 'Not Found' }))
  })

  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  origin = `http://127.0.0.1:${(server.address() as AddressInfo).port}`

  // 业务代码里的 URL 是 `/api/...` 相对路径，浏览器会补 origin，node fetch 需要手动补
  globalThis.fetch = ((input, init) => nativeFetch(`${origin}${String(input)}`, init)) as typeof fetch
})

after(() => {
  globalThis.fetch = nativeFetch
  server.closeAllConnections()
  server.close()
})

test('真实 HTTP 流：stage / delta / done 都能按帧收到', async () => {
  const stages: string[] = []
  let streamed = ''

  const result = await api.submitAnswerStreamApi(
    'happy',
    { answer: '我的回答' },
    {
      onStage: (event) => stages.push(event.label),
      onDelta: (event) => {
        streamed += event.text
      },
    },
  )

  assert.deepEqual(stages, ['正在生成问题'])
  assert.equal(streamed, '那你介绍一下支付模块')
  assert.equal(result.round_no, 2)
  assert.equal(result.next_question, '那你介绍一下支付模块')
  assert.equal(result.is_finished, false)
})

test('流内 error 事件带 detail 抛出 SubmitAnswerStreamError', async () => {
  let streamed = ''

  await assert.rejects(
    api.submitAnswerStreamApi('error-event', { answer: '回答' }, {
      onDelta: (event) => {
        streamed += event.text
      },
    }),
    (error: unknown) => {
      assert.ok(error instanceof api.SubmitAnswerStreamError)
      assert.equal(error.detail, 'LLM provider error: timeout')
      return true
    },
  )

  assert.equal(streamed, '半截题')
})

test('流提前关闭没有 done：抛中断错误，交给调用方降级', async () => {
  await assert.rejects(api.submitAnswerStreamApi('no-done', { answer: '回答' }), (error: unknown) => {
    assert.ok(error instanceof api.SubmitAnswerStreamError)
    assert.match(error.detail, /流式响应中断/)
    return true
  })
})

test('AbortSignal 能立刻掐断还在等待的流', async () => {
  const controller = new AbortController()
  const stages: string[] = []

  const promise = api.submitAnswerStreamApi(
    'abort',
    { answer: '回答' },
    { onStage: (event) => stages.push(event.label) },
    controller.signal,
  )

  const startedAt = Date.now()
  while (!stages.length) {
    assert.ok(Date.now() - startedAt < 2000, '没等到 stage 事件')
    await sleep(5)
  }

  controller.abort()

  await assert.rejects(promise, (error: unknown) => {
    assert.equal((error as { name?: string }).name, 'AbortError')
    return true
  })
})
