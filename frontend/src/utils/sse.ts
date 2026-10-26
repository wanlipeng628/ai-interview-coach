export interface SseEvent {
  event: string
  data: string
}

export interface SseParser {
  /** 追加一段原始文本，返回其中已经完整的事件 */
  push(chunk: string): SseEvent[]
  /** 流结束时调用，吐出没有以空行收尾的最后一段事件 */
  flush(): SseEvent[]
}

const DEFAULT_EVENT = 'message'

const parseBlock = (block: string): SseEvent | null => {
  let event = DEFAULT_EVENT
  const dataLines: string[] = []

  for (const line of block.split('\n')) {
    // 空行已在上层切分时处理掉；以冒号开头的是注释（心跳包常用）
    if (!line || line.startsWith(':')) continue

    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    let value = colon === -1 ? '' : line.slice(colon + 1)
    // 规范规定字段值前最多去掉一个空格
    if (value.startsWith(' ')) value = value.slice(1)

    if (field === 'event') {
      event = value.trim() || DEFAULT_EVENT
    } else if (field === 'data') {
      dataLines.push(value)
    }
  }

  if (!dataLines.length) return null
  return { event, data: dataLines.join('\n') }
}

/**
 * 极简 SSE 解析器：按空行切事件，解析 `event:` / `data:` 两行。
 * 网络分片可能把一行甚至一个中文汉字切断，所以未收尾的内容留在 buffer 里等下一片。
 */
export const createSseParser = (): SseParser => {
  let buffer = ''

  const drain = (): SseEvent[] => {
    const events: SseEvent[] = []
    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const parsed = parseBlock(block)
      if (parsed) events.push(parsed)
      boundary = buffer.indexOf('\n\n')
    }
    return events
  }

  return {
    push(chunk) {
      // 兼容 CRLF；被切断的 \r\n 会在下一片拼回来之后一起归一化
      buffer = (buffer + chunk).replace(/\r\n/g, '\n')
      return drain()
    },
    flush() {
      const rest = buffer.replace(/\r\n/g, '\n').trim()
      buffer = ''
      const parsed = rest ? parseBlock(rest) : null
      return parsed ? [parsed] : []
    },
  }
}

/**
 * 读完一整条 SSE 流，把事件逐个交给 onEvent。
 * onEvent 返回非 null 表示「够了」（比如收到 done），立即结束读取并把它作为结果返回。
 * 流里没出现这类事件就返回 null，由调用方判断是收尾还是中断。
 */
export const readSseStream = async <T>(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: SseEvent) => T | null,
): Promise<T | null> => {
  const reader = stream.getReader()
  const decoder = new TextDecoder('utf-8')
  const parser = createSseParser()

  const emit = (events: SseEvent[]): T | null => {
    for (const event of events) {
      const result = onEvent(event)
      if (result !== null) return result
    }
    return null
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        // 收尾：先冲掉解码器残余，再吐出没以空行结尾的最后一段
        return emit(parser.push(decoder.decode())) ?? emit(parser.flush())
      }

      const result = emit(parser.push(decoder.decode(value, { stream: true })))
      if (result !== null) return result
    }
  } finally {
    // 提前结束（done / 出错 / abort）时主动断开，避免 keep-alive 把连接挂住
    reader.cancel().catch(() => {})
  }
}
