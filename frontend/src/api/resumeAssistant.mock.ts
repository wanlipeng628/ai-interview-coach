// 并行开发兜底：后端 /api/resume/assistant/* 尚未就绪时（404 / 接口不可达），
// 用本地脚本对话驱动页面，接口契约与 resumeAssistant.api.ts 完全一致。
// 后端上线后真实请求会成功，本模块不再被触发，可整文件删除。
import type {
  ResumeAssistantAnswerResponse,
  ResumeAssistantDetailResponse,
  ResumeAssistantFinalizeResponse,
  ResumeAssistantStartResponse,
  StartResumeAssistantRequest,
} from './resumeAssistant.api'
import type { AssistantProgress, ResumeSection, ResumeStage } from '@/types/resumeAssistant'
import { uuid } from '@/utils/uuid'

interface SectionScript {
  key: ResumeSection
  label: string
  question: string
  hint: string
}

const SCRIPT: SectionScript[] = [
  {
    key: 'BASIC',
    label: '基本信息',
    question: '先做个自我介绍吧——姓名、工作年限、目前岗位和目标岗位分别是什么？',
    hint: '示例：张明，4 年 Java 后端，目前在电商公司负责订单中台，目标岗位是 AI 应用开发工程师。',
  },
  {
    key: 'EDUCATION',
    label: '教育背景',
    question: '说说你的教育背景：学校、专业、学历和毕业时间。',
    hint: '示例：2016–2020 就读于 XX 大学 计算机科学与技术专业，本科。',
  },
  {
    key: 'WORK',
    label: '工作经历',
    question: '挑一段最有代表性的工作经历：公司、时间、你的职责和主要成果。',
    hint: '示例：2021.06 至今在 XX 公司负责订单中台，主导分库分表改造，把大促峰值 QPS 提升 3 倍。',
  },
  {
    key: 'PROJECT',
    label: '项目经历',
    question: '挑一个能体现你能力的项目：背景、你负责的部分和最终效果。',
    hint: '示例：主导 Redis + 本地多级缓存重构，将核心接口 P99 从 800ms 降到 120ms。',
  },
  {
    key: 'SKILL',
    label: '技能栈',
    question: '你熟悉哪些技术栈？可以按语言、框架、中间件、工具分类说。',
    hint: '示例：Java / Spring Boot / MySQL / Redis / Kafka / Docker / Kubernetes。',
  },
  {
    key: 'INTENT',
    label: '求职意向',
    question: '最后说说你的求职意向：期望岗位、城市、薪资范围和到岗时间。',
    hint: '示例：AI 应用开发工程师，杭州，期望 30–40K，一个月内到岗。',
  },
]

interface MockDraft {
  title: string
  answers: Partial<Record<ResumeSection, string>>
  notes: string[]
}

const STORAGE_PREFIX = 'resumeAssistant.mock.'

const loadDraft = (draftId: string): MockDraft | null => {
  try {
    const raw = sessionStorage.getItem(STORAGE_PREFIX + draftId)
    return raw ? (JSON.parse(raw) as MockDraft) : null
  } catch {
    return null
  }
}

const saveDraft = (draftId: string, draft: MockDraft) => {
  try {
    sessionStorage.setItem(STORAGE_PREFIX + draftId, JSON.stringify(draft))
  } catch {
    // 隐私模式下 sessionStorage 不可用，降级为仅当次会话内存态
  }
}

const completedSections = (draft: MockDraft): ResumeSection[] =>
  SCRIPT.filter((item) => draft.answers[item.key]).map((item) => item.key)

const currentStage = (draft: MockDraft): ResumeStage => {
  const answered = completedSections(draft).length
  if (answered >= SCRIPT.length) return 'DONE'
  return SCRIPT[answered].key
}

const buildProgress = (draft: MockDraft): AssistantProgress => ({
  completed: completedSections(draft),
  current: currentStage(draft),
})

const buildMarkdown = (draft: MockDraft): string => {
  const blocks = SCRIPT.map((item) => {
    const answer = draft.answers[item.key]
    return answer ? `## ${item.label}\n${answer}` : ''
  }).filter(Boolean)

  if (draft.notes.length) {
    blocks.push(`## 补充说明\n${draft.notes.map((note) => `- ${note}`).join('\n')}`)
  }
  return `# ${draft.title}\n\n${blocks.join('\n\n')}`
}

const delay = <T>(value: T): Promise<T> =>
  new Promise((resolve) => window.setTimeout(() => resolve(value), 320))

export const mockStartResumeAssistant = (
  data: StartResumeAssistantRequest,
): Promise<ResumeAssistantStartResponse> => {
  const draftId = `mock-${uuid()}`
  const draft: MockDraft = { title: data.title?.trim() || '默认简历', answers: {}, notes: [] }
  saveDraft(draftId, draft)
  console.info('[简历助手] 后端未就绪，已启用本地演示数据')
  return delay({
    draft_id: draftId,
    status: 'IN_PROGRESS',
    stage: 'BASIC',
    question: SCRIPT[0].question,
    hint: SCRIPT[0].hint,
    progress: buildProgress(draft),
  })
}

export const mockSubmitResumeAnswer = (
  draftId: string,
  answer: string,
): Promise<ResumeAssistantAnswerResponse> => {
  const draft = loadDraft(draftId)
  if (!draft) return Promise.reject(new Error('本地演示草稿不存在'))

  const stage = currentStage(draft)
  if (stage === 'DONE') {
    draft.notes.push(answer)
    saveDraft(draftId, draft)
    return delay({
      draft_id: draftId,
      status: 'IN_PROGRESS',
      stage: 'DONE',
      question: '已记录这条补充。你可以继续补充，或点击「生成简历」完成。',
      hint: null,
      ready_to_finalize: true,
      progress: buildProgress(draft),
    })
  }

  draft.answers[stage] = answer
  saveDraft(draftId, draft)
  const nextIndex = completedSections(draft).length
  const next = SCRIPT[nextIndex]
  return delay({
    draft_id: draftId,
    status: 'IN_PROGRESS',
    stage: next ? next.key : 'DONE',
    question: next ? next.question : null,
    hint: next ? next.hint : null,
    ready_to_finalize: !next,
    progress: buildProgress(draft),
  })
}

export const mockFinalizeResumeAssistant = (
  draftId: string,
): Promise<ResumeAssistantFinalizeResponse> => {
  const draft = loadDraft(draftId)
  if (!draft) return Promise.reject(new Error('本地演示草稿不存在'))
  const content = buildMarkdown(draft)
  return delay({
    draft_id: draftId,
    profile_id: 'mock-profile',
    title: draft.title,
    content,
    summary: `AI 引导生成的简历，已填写 ${completedSections(draft).length} 个模块。`,
  })
}

export const mockGetResumeAssistant = (draftId: string): Promise<ResumeAssistantDetailResponse> => {
  const draft = loadDraft(draftId)
  if (!draft) return Promise.reject(new Error('本地演示草稿不存在'))

  const messages: ResumeAssistantDetailResponse['messages'] = []
  const answeredCount = completedSections(draft).length
  SCRIPT.forEach((item, index) => {
    const answer = draft.answers[item.key]
    if (answer) {
      messages.push({ role: 'AI', content: item.question, hint: item.hint, stage: item.key })
      messages.push({ role: 'USER', content: answer, stage: item.key })
      return
    }
    // 首个未回答的分节即当前提问，恢复时保留在对话末尾
    if (index === answeredCount) {
      messages.push({ role: 'AI', content: item.question, hint: item.hint, stage: item.key })
    }
  })
  if (currentStage(draft) === 'DONE') {
    messages.push({
      role: 'AI',
      content: '信息已经收集完整，点击「生成简历」即可生成你的简历。',
      stage: 'DONE',
    })
  }
  draft.notes.forEach((note) => messages.push({ role: 'USER', content: note }))

  return delay({
    draft_id: draftId,
    status: 'IN_PROGRESS',
    stage: currentStage(draft),
    messages,
    sections: {},
    progress: buildProgress(draft),
  })
}
