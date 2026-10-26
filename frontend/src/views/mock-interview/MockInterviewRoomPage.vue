<template>
  <div class="interview-page" :style="roomStyle">
    <aside class="left-pane">
      <InterviewInfoPanel :info="interview.info" />
    </aside>

    <main class="center-pane">
      <PageHeader
        variant="toolbar"
        eyebrow="AI 模拟面试"
        :title="interview.info.jobRole"
      >
        <template #leading>
          <el-button
            v-if="isMobile"
            class="room-header__back"
            text
            :icon="ArrowLeft"
            aria-label="返回面试准备页"
            @click="router.push('/mock-interview')"
          />
        </template>
        <template #actions>
          <el-tag size="large" effect="light">聊天式面试</el-tag>
        </template>
      </PageHeader>

      <InterviewChatPanel :messages="interview.messages" />
      <InterviewInputBar
        :disabled="interview.loading || interview.isStreaming || interview.info.status === 'finished'"
        :generating="interview.generating"
        :is-streaming="interview.isStreaming"
        :error-message="interview.errorMessage"
        :failed-draft="interview.failedDraft"
        @send="interview.submitAnswer"
        @finish="handleFinish"
        @clear-error="interview.errorMessage = ''"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PageHeader from '@/components/common/PageHeader.vue'
import InterviewChatPanel from '@/components/interview/InterviewChatPanel.vue'
import InterviewInfoPanel from '@/components/interview/InterviewInfoPanel.vue'
import InterviewInputBar from '@/components/interview/InterviewInputBar.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useInterviewStore } from '@/stores/interview.store'

const interview = useInterviewStore()
const router = useRouter()
const route = useRoute()
let durationTimer: number | undefined

const isMobile = useMediaQuery('(max-width: 768px)')
const roomHeight = ref('')

// 仅移动端生效：跟随 visualViewport 高度，避免软键盘弹出后输入栏被遮挡
const roomStyle = computed(() => (roomHeight.value ? { height: roomHeight.value } : undefined))

const syncViewportHeight = () => {
  const viewport = window.visualViewport
  if (!viewport || !isMobile.value) {
    roomHeight.value = ''
    return
  }
  roomHeight.value = `${Math.round(viewport.height)}px`
}

const handleFinish = async () => {
  await ElMessageBox.confirm('结束后将进入报告生成阶段，是否确认结束本次面试？', '结束面试', {
    confirmButtonText: '确认结束',
    cancelButtonText: '继续面试',
    type: 'warning',
  })
  await interview.finishInterview()
  router.push(`/report/${interview.info.sessionId}`)
}

watch(isMobile, syncViewportHeight)

onMounted(() => {
  const routeSessionId = String(route.params.sessionId || '')
  if (!routeSessionId) {
    ElMessage.warning('当前面试会话未初始化，请先从准备页开始面试')
    router.replace('/mock-interview')
    return
  }

  syncViewportHeight()
  window.visualViewport?.addEventListener('resize', syncViewportHeight)
  window.visualViewport?.addEventListener('scroll', syncViewportHeight)

  interview
    .restoreInterview(routeSessionId)
    .then(() => {
      durationTimer = window.setInterval(() => interview.tickDuration(), 1000)
    })
    .catch(() => {
      ElMessage.warning('当前面试会话无法恢复，请先从准备页重新开始')
      router.replace('/mock-interview')
    })
})

onBeforeUnmount(() => {
  window.visualViewport?.removeEventListener('resize', syncViewportHeight)
  window.visualViewport?.removeEventListener('scroll', syncViewportHeight)
  if (durationTimer) window.clearInterval(durationTimer)
  // 离开房间就别让 SSE 流挂着
  interview.cancelStream()
})
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.interview-page {
  height: 100vh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
  padding: 20px;
  overflow: hidden;
}

.left-pane {
  min-height: 0;
}

// 房间本体：一块暖白面，页头 / 对话 / 输入栏都长在它上面，不再各自成为一张卡
.center-pane {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 16px 16px;
  background: var(--c-chat-bg);
  border-radius: 22px;
  overflow: hidden;
}

// 工具栏页头在房间里退成一条低调的状态条
.center-pane :deep(.page-header--toolbar) {
  padding: 18px 4px 4px;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.center-pane :deep(.page-header__actions .el-tag) {
  --el-tag-bg-color: transparent;
  --el-tag-border-color: var(--c-chat-line);
  --el-tag-text-color: var(--c-chat-quiet);
}

@media (max-width: 1280px) {
  .interview-page {
    height: auto;
    min-height: 100vh;
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .center-pane {
    min-height: 720px;
  }
}

// 移动端整页作为独立全屏房间：固定定位、跟随 visualViewport 高度、底部留出安全区
@include mobile {
  .interview-page {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 30;
    height: 100dvh;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 0;
    padding: 0;
    padding-top: env(safe-area-inset-top, 0px);
    background: var(--c-chat-bg);
    overflow: hidden;
  }

  .left-pane {
    flex: 0 0 auto;
    padding: 8px 14px 0;
  }

  // 房间信息在手机上不再是卡片，只留一行轻量状态
  .left-pane :deep(.el-card) {
    background: transparent;
    border: none;
    box-shadow: none;
  }

  .left-pane :deep(.el-card__header) {
    padding: 0;
    border-bottom: none;
  }

  .left-pane :deep(.el-card__body) {
    padding: 0;
  }

  // 折叠开关在房间里退成次要文字，不抢第—眼
  .left-pane :deep(.info-panel__toggle) {
    color: var(--c-chat-quiet);
  }

  .center-pane {
    flex: 1;
    min-height: 0;
    gap: 6px;
    padding: 0 0 calc(10px + #{$safe-bottom});
    border-radius: 0;
  }

  .center-pane :deep(.page-header--toolbar) {
    padding: 8px 6px 2px;
  }

  .room-header__back {
    min-height: $touch-target;
    min-width: $touch-target;
    margin-left: -8px;
  }
}
</style>
