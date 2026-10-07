// 轻量 Markdown 渲染：不引入新依赖，覆盖简历所需的最小语法子集。
// 先整体 HTML 转义再解析，确保 v-html 渲染 LLM 文本时不会执行注入的标签。
const escapeHtml = (value: string) =>
  value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

const renderInline = (value: string) =>
  value
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')

// 结果弹层已单独展示简历标题，去掉正文开头重复的一级标题（仅匹配 `# `，不误伤 `## `）
export const stripLeadingHeading = (markdown: string) =>
  (markdown ?? '').replace(/^\s*#\s[^\n]*\r?\n+/, '')

export const renderMarkdown = (markdown: string): string => {
  const lines = escapeHtml(markdown ?? '').split(/\r?\n/)
  const html: string[] = []
  let listType: 'ul' | 'ol' | null = null

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`)
      listType = null
    }
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      closeList()
      continue
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(trimmed)
    if (heading) {
      closeList()
      const level = heading[1].length
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`)
      continue
    }

    const unordered = /^[-*+]\s+(.*)$/.exec(trimmed)
    if (unordered) {
      if (listType !== 'ul') {
        closeList()
        html.push('<ul>')
        listType = 'ul'
      }
      html.push(`<li>${renderInline(unordered[1])}</li>`)
      continue
    }

    const ordered = /^\d+[.)]\s+(.*)$/.exec(trimmed)
    if (ordered) {
      if (listType !== 'ol') {
        closeList()
        html.push('<ol>')
        listType = 'ol'
      }
      html.push(`<li>${renderInline(ordered[1])}</li>`)
      continue
    }

    closeList()
    html.push(`<p>${renderInline(trimmed)}</p>`)
  }

  closeList()
  return html.join('\n')
}
