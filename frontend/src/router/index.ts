import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import DashboardPage from '@/views/dashboard/DashboardPage.vue'
import AbilityProfilePage from '@/views/profile/AbilityProfilePage.vue'
import InterviewHistoryPage from '@/views/history/InterviewHistoryPage.vue'
import InterviewReportPage from '@/views/report/InterviewReportPage.vue'
import MockInterviewPreparePage from '@/views/mock-interview/MockInterviewPreparePage.vue'
import MockInterviewRoomPage from '@/views/mock-interview/MockInterviewRoomPage.vue'
import TrainingPage from '@/views/training/TrainingPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: DashboardPage,
          meta: { title: '首页概览' },
        },
        {
          path: 'mock-interview',
          name: 'MockInterview',
          component: MockInterviewPreparePage,
          meta: { title: 'AI 模拟面试' },
        },
        {
          path: 'mock-interview/:sessionId',
          name: 'MockInterviewRoom',
          component: MockInterviewRoomPage,
          meta: { title: 'AI 模拟面试' },
        },
        {
          path: 'report',
          name: 'InterviewReportHome',
          component: InterviewReportPage,
          meta: { title: '面试报告' },
        },
        {
          path: 'report/:sessionId',
          name: 'InterviewReport',
          component: InterviewReportPage,
          meta: { title: '面试报告' },
        },
        {
          path: 'ability-profile',
          name: 'AbilityProfile',
          component: AbilityProfilePage,
          meta: { title: '能力画像' },
        },
        {
          path: 'training',
          name: 'Training',
          component: TrainingPage,
          meta: { title: '专项训练' },
        },
        {
          path: 'interview-history',
          name: 'InterviewHistory',
          component: InterviewHistoryPage,
          meta: { title: '面试历史' },
        },
      ],
    },
  ],
})

export default router
