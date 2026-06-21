export interface ResumeProfile {
  id: number
  title: string
  content: string
  summary?: string | null
  isDefault: boolean
  updateTime: string
}
