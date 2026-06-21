import { defineStore } from 'pinia'

import { getResumeProfileApi, saveResumeProfileApi } from '@/api/resume.api'
import type { ResumeProfile } from '@/types/resume'

export const useResumeStore = defineStore('resume', {
  state: () => ({
    profile: null as ResumeProfile | null,
    loading: false,
    saving: false,
    errorMessage: '',
  }),

  actions: {
    async fetchProfile() {
      this.loading = true
      this.errorMessage = ''
      try {
        const profile = await getResumeProfileApi()
        this.profile = {
          id: profile.id,
          title: profile.title,
          content: profile.content,
          summary: profile.summary,
          isDefault: profile.is_default,
          updateTime: profile.update_time,
        }
      } catch (error) {
        this.profile = null
        this.errorMessage = getErrorMessage(error)
      } finally {
        this.loading = false
      }
    },

    async saveProfile(title: string, content: string) {
      this.saving = true
      this.errorMessage = ''
      try {
        await saveResumeProfileApi({ title, content })
        await this.fetchProfile()
      } finally {
        this.saving = false
      }
    },
  },
})

const getErrorMessage = (error: unknown) => {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: string } } }).response
    if (response?.status === 404) return ''
    return response?.data?.detail ?? '简历加载失败'
  }
  return '简历加载失败'
}
