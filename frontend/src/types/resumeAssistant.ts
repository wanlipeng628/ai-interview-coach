export type ResumeSection = 'BASIC' | 'EDUCATION' | 'WORK' | 'PROJECT' | 'SKILL' | 'INTENT'

export type ResumeStage = ResumeSection | 'DONE'

export interface AssistantProgress {
  completed: ResumeSection[]
  current: ResumeStage
}

export interface AssistantMessage {
  id: string
  role: 'ai' | 'user'
  content: string
  hint?: string | null
  createdAt: string
}

export interface ResumeResult {
  draftId: string
  profileId: number | string | null
  title: string
  content: string
  summary: string
}

export interface ResumeSectionMeta {
  key: ResumeSection
  label: string
}

// 分节展示顺序，与后端 BASIC → EDUCATION → WORK → PROJECT → SKILL → INTENT → DONE 保持一致
export const RESUME_SECTIONS: ResumeSectionMeta[] = [
  { key: 'BASIC', label: '基本信息' },
  { key: 'EDUCATION', label: '教育背景' },
  { key: 'WORK', label: '工作经历' },
  { key: 'PROJECT', label: '项目经历' },
  { key: 'SKILL', label: '技能栈' },
  { key: 'INTENT', label: '求职意向' },
]
