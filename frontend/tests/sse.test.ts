import assert from 'node:assert/strict'
import { test } from 'node:test'

import { createSseParser, readSseStream } from '../src/utils/sse.ts'

const streamOf = (chunks: Uint8Array[]) =>
  new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk)
      controller.close()
    },
  })

const encoder = new TextEncoder()

test('按空行切事件并解析 event/data', () => {
  const parser = createSseParser()
  const events = parser.push(
    'event: stage\ndata: {"stage":"generating","label":"正在生成问题"}\n\n' +
      'event: delta\ndata: {"text":"那你"}\n\n',
  )

  assert.deepEqual(events, [
    { event: 'stage', data: '{"stage":"generating","label":"正在生成问题"}' },
    { event: 'delta', data: '{"text":"那你"}' },
  ])
})

test('分片切断时缓存到下一片再解析', () => {
  const parser = createSseParser()

  assert.deepEqual(parser.push('event: delta\ndata: {"tex'), [])
  assert.deepEqual(parser.push('t":"那你'), [])
  assert.deepEqual(parser.push('当时为什么"}\n'), [])
  assert.deepEqual(parser.push('\n'), [{ event: 'delta', data: '{"text":"那你当时为什么"}' }])
})

test('兼容 CRLF，包括被切断的 \\r\\n', () => {
  const parser = createSseParser()

  assert.deepEqual(parser.push('event: delta\r\ndata: {"text":"a"}\r'), [])
  assert.deepEqual(parser.push('\n\r\n'), [{ event: 'delta', data: '{"text":"a"}' }])
})

test('忽略注释、心跳字段与空 data 区块', () => {
  const parser = createSseParser()
  const events = parser.push(': ping\n\nretry: 3000\n\nid: 7\nevent: done\ndata: {}\n\n')

  assert.deepEqual(events, [{ event: 'done', data: '{}' }])
})

test('多行 data 用换行拼接', () => {
  const parser = createSseParser()
  assert.deepEqual(parser.push('event: note\ndata: 第一行\ndata: 第二行\n\n'), [
    { event: 'note', data: '第一行\n第二行' },
  ])
})

test('没有 event 字段时默认 message', () => {
  const parser = createSseParser()
  assert.deepEqual(parser.push('data: {"text":"hi"}\n\n'), [
    { event: 'message', data: '{"text":"hi"}' },
  ])
})

test('flush 吐出没以空行结尾的最后一段', () => {
  const parser = createSseParser()
  assert.deepEqual(parser.push('event: done\ndata: {"round_no":2}'), [])
  assert.deepEqual(parser.flush(), [{ event: 'done', data: '{"round_no":2}' }])
  assert.deepEqual(parser.flush(), [])
})

test('readSseStream 逐片解码，多字节字符被切开也能拼回', async () => {
  const bytes = encoder.encode(
    'event: delta\ndata: {"text":"你好"}\n\nevent: done\ndata: {"round_no":2}\n\n',
  )
  // 从「你」的第一个字节之后切开：一个汉字的 3 个字节横跨两片
  const cut = bytes.indexOf(0xe4) + 1
  const seen: string[] = []

  const result = await readSseStream(streamOf([bytes.slice(0, cut), bytes.slice(cut)]), (event) => {
    seen.push(`${event.event}:${event.data}`)
    return event.event === 'done' ? JSON.parse(event.data) : null
  })

  assert.deepEqual(seen, ['delta:{"text":"你好"}', 'done:{"round_no":2}'])
  assert.deepEqual(result, { round_no: 2 })
})

test('readSseStream 收到结果就停，不再消费后面的分片', async () => {
  let pulls = 0
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      pulls += 1
      controller.enqueue(
        pulls === 1
          ? encoder.encode('event: done\ndata: {"round_no":2}\n\n')
          : encoder.encode('event: delta\ndata: {"text":"不该出现"}\n\n'),
      )
      if (pulls > 2) controller.close()
    },
  })

  const deltas: string[] = []
  const result = await readSseStream(stream, (event) => {
    if (event.event === 'delta') deltas.push(event.data)
    return event.event === 'done' ? event.data : null
  })

  assert.equal(result, '{"round_no":2}')
  assert.deepEqual(deltas, [])
})

test('readSseStream 流结束仍没有结果时返回 null（交给调用方降级）', async () => {
  const result = await readSseStream(
    streamOf([encoder.encode('event: stage\ndata: {"stage":"generating","label":"正在生成"}')]),
    () => null,
  )

  assert.equal(result, null)
})
