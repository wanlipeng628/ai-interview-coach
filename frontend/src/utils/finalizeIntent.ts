// 判断用户输入是否为「直接生成简历」的短指令：整句匹配，避免正常回答误触发。
// 例：命中「帮我生成吧」「生成简历」；不命中「我在上一家公司负责生成简历相关的功能模块」。
const FINALIZE_PATTERN =
  /^(帮我|帮忙|请|直接)?(生成|输出|导出|出)(一份|一个|个|一下)?(简历|出来|吧)?[！!。.~～]*$/

export const isFinalizeRequest = (text: string) => {
  const value = (text ?? '').trim()
  return value.length > 0 && value.length <= 12 && FINALIZE_PATTERN.test(value)
}
