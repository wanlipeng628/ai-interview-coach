export interface TrainingTopic {
  id: string
  title: string
  description: string
  progress: number
  difficulty: '初级' | '中级' | '高级'
  duration: string
}

export interface TrainingPlan {
  title: string
  description: string
  estimatedTime: string
  topics: number
}
