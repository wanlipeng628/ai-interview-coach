export interface KnowledgeNode {
  name: string
  score: number
  status: '掌握良好' | '需要巩固' | '薄弱'
}

export interface ProfileRadarItem {
  name: string
  value: number
}

export interface MasterySlice {
  name: string
  value: number
}
