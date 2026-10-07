import assert from 'node:assert/strict'
import { test } from 'node:test'

import { isFinalizeRequest } from '../src/utils/finalizeIntent.ts'
import { renderMarkdown, stripLeadingHeading } from '../src/utils/markdown.ts'

test('renderMarkdown 转义注入并渲染标题/列表/粗体', () => {
  const html = renderMarkdown('# 标题\n\n## 分节\n\n- 条目 **加粗**\n\n<script>alert(1)</script>')
  assert.match(html, /<h1>标题<\/h1>/)
  assert.match(html, /<h2>分节<\/h2>/)
  assert.match(html, /<li>条目 <strong>加粗<\/strong><\/li>/)
  assert.ok(!/<script>/.test(html), '不应输出原始 script 标签')
  assert.match(html, /&lt;script&gt;/)
})

test('stripLeadingHeading 仅去掉首个一级标题', () => {
  assert.equal(stripLeadingHeading('# 默认简历\n\n## 基本信息\n内容'), '## 基本信息\n内容')
  assert.equal(stripLeadingHeading('## 基本信息\n内容'), '## 基本信息\n内容')
})

test('isFinalizeRequest 仅命中整句短指令', () => {
  for (const hit of ['帮我生成吧', '生成简历', '帮我生成一份简历', '生成吧', '直接生成']) {
    assert.equal(isFinalizeRequest(hit), true, `应命中: ${hit}`)
  }
  for (const miss of [
    '我在上一家公司负责生成简历相关的功能模块',
    '可以生成',
    '我做过简历生成工具的优化',
    '',
    '简历',
  ]) {
    assert.equal(isFinalizeRequest(miss), false, `不应命中: ${miss}`)
  }
})
