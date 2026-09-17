<template>
  <div class="interview-page" :style="roomStyle">
    <aside class="left-pane">
      <InterviewInfoPanel :info="interview.info" />
    </aside>

    <main class="center-pane">
      <div class="room-header">
        <el-button
          v-if="isMobile"
          class="room-header__back"
          text
          :icon="ArrowLeft"
          aria-label="返回面试准备页"
          @click="router.push('/mock-interview')"
        />
        <div>
          <p>AI 模拟面试</p>
          <h1>{{ interview.info.jobRole }}</h1>
        </div>
        <el-tag size="large" effect="light">聊天式面试</el-tag>
      </div>

      <InterviewChatPanel :messages="interview.messages" />
      <el-alert
        v-if="interview.errorMessage"
        :title="interview.errorMessage"
        type="error"
        show-icon
        :closable="false"
      />
      <InterviewInputBar
        :disabled="interview.loading || interview.isStreaming || interview.info.status === 'finished'"
        :generating="interview.generating"
        @send="interview.submitAnswer"
        @finish="handleFinish"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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

.left-pane,
.center-pane {
  min-height: 0;
}

.center-pane {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto auto;
  gap: 16px;
}

.room-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 8px;
  background: #fff;

  p {
    margin: 0 0 6px;
    color: #2f6bff;
    font-weight: 700;
  }

  h1 {
    margin: 0;
    color: #101828;
    font-size: 22px;
  }
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
    gap: 10px;
    padding: 10px;
    padding-bottom: calc(10px + #{$safe-bottom});
    background: #f5f7fb;
    overflow: hidden;
  }

  .left-pane {
    flex: 0 0 auto;
  }

  .center-pane {
    flex: 1;
    gap: 10px;
    min-height: 0;
  }

  .room-header {
    gap: 10px;
    padding: 12px 14px;

    > div {
      flex: 1;
      min-width: 0;
    }

    h1 {
      font-size: 17px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .room-header__back {
    min-height: $touch-target;
    min-width: $touch-target;
    margin-left: -8px;
  }
}
</style>
