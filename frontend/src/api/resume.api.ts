import request from './request'

export interface ResumeProfileResponse {
  id: number
  title: string
  content: string
  summary?: string | null
  is_default: boolean
  update_time: string
}

export interface SaveResumeProfileRequest {
  title: string
  content: string
}

export interface SuccessResponse {
  success: boolean
}

export const getResumeProfileApi = () =>
  request.get<ResumeProfileResponse, ResumeProfileResponse>('/resume/profile')

export const saveResumeProfileApi = (data: SaveResumeProfileRequest) =>
  request.put<SuccessResponse, SuccessResponse>('/resume/profile', data)
