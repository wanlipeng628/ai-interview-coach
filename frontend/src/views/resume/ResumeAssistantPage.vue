<template>
  <div class="assistant-page" :style="pageStyle">
    <aside class="side-pane">
      <AssistantProgressPanel :progress="assistant.progress" />
    </aside>

    <main class="chat-pane">
      <PageHeader
        variant="toolbar"
        eyebrow="简历助手"
        :title="headerTitle"
        description="通过几轮对话梳理经历，AI 帮你生成一份结构化简历。"
      >
        <template #leading>
          <el-button
            v-if="isMobile"
            class="chat-pane__back"
            text
            :icon="ArrowLeft"
            aria-label="返回我的简历"
            @click="goResume"
          />
        </template>
        <template #actions>
          <el-tag v-if="assistant.usingMock" type="warning" size="large" effect="light">
            本地演示数据
          </el-tag>
          <el-tag v-else size="large" effect="light">对话引导</el-tag>
        </template>
      </PageHeader>

      <AssistantChatPanel
        :messages="assistant.messages"
        :starting="assistant.starting"
        :pending="assistant.submitting || assistant.finalizing"
      />

      <el-alert
        v-if="assistant.errorMessage"
        :title="assistant.errorMessage"
        type="error"
        show-icon
        :closable="false"
      >
        <el-button v-if="!assistant.messages.length" size="small" @click="initialize">重试</el-button>
      </el-alert>

      <AssistantInputBar
        :disabled="inputDisabled"
        :sending="assistant.submitting"
        :finalizing="assistant.finalizing"
        :generating="assistant.submitting || assistant.finalizing"
        :ready-to-finalize="assistant.readyToFinalize"
        @send="handleSend"
        @finalize="handleFinalize"
      />
    </main>

    <AssistantResultDialog
      v-model="resultVisible"
      :result="assistant.result"
      @save="handleSave"
      @continue="handleContinue"
      @interview="goInterview"
    />
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PageHeader from '@/components/common/PageHeader.vue'
import AssistantChatPanel from '@/components/resume/AssistantChatPanel.vue'
import AssistantInputBar from '@/components/resume/AssistantInputBar.vue'
import AssistantProgressPanel from '@/components/resume/AssistantProgressPanel.vue'
import AssistantResultDialog from '@/components/resume/AssistantResultDialog.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useResumeAssistantStore } from '@/stores/resumeAssistant.store'

const assistant = useResumeAssistantStore()
const router = useRouter()
const route = useRoute()

const isMobile = useMediaQuery('(max-width: 768px)')
const resultVisible = ref(false)
const pageHeight = ref('')

// 仅移动端生效：跟随 visualViewport 高度，避免软键盘弹出后输入栏被遮挡
const pageStyle = computed(() => (pageHeight.value ? { height: pageHeight.value } : undefined))

const headerTitle = computed(() =>
  assistant.progress.current === 'DONE' ? '信息已收集，可以生成简历' : '让 AI 引导你写简历',
)

const inputDisabled = computed(
  () => assistant.starting || assistant.submitting || assistant.finalizing,
)

const syncViewportHeight = () => {
  const viewport = window.visualViewport
  if (!viewport || !isMobile.value) {
    pageHeight.value = ''
    return
  }
  pageHeight.value = `${Math.round(viewport.height)}px`
}

const initialize = async () => {
  const draftId = String(route.query.draft || '')
  try {
    if (draftId) {
      await assistant.restore(draftId)
    } else {
      await assistant.start()
      if (assistant.draftId) {
        router.replace({ query: { draft: assistant.draftId } })
      }
    }
  } catch {
    // 错误信息已写入 store，由模板中的错误提示展示
  }
}

const handleSend = async (answer: string) => {
  try {
    await assistant.sendAnswer(answer)
  } catch {
    ElMessage.error(assistant.errorMessage || '提交回答失败，请稍后重试')
  }
}

const handleFinalize = async () => {
  try {
    await assistant.finalize()
  } catch {
    ElMessage.error(assistant.errorMessage || '生成简历失败，请稍后重试')
  }
}

const handleSave = () => {
  ElMessage.success('简历已保存到「我的简历」')
}

const handleContinue = () => {
  resultVisible.value = false
}

const goInterview = () => {
  resultVisible.value = false
  router.push('/mock-interview')
}

const goResume = () => {
  router.push('/resume')
}

watch(
  () => assistant.result,
  (result) => {
    if (result) resultVisible.value = true
  },
)

watch(isMobile, syncViewportHeight)

onMounted(() => {
  syncViewportHeight()
  window.visualViewport?.addEventListener('resize', syncViewportHeight)
  window.visualViewport?.addEventListener('scroll', syncViewportHeight)
  initialize()
})

onBeforeUnmount(() => {
  window.visualViewport?.removeEventListener('resize', syncViewportHeight)
  window.visualViewport?.removeEventListener('scroll', syncViewportHeight)
})
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.assistant-page {
  height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
  padding: 20px;
  overflow: hidden;
}

.side-pane,
.chat-pane {
  min-height: 0;
}

.chat-pane {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto auto;
  gap: 16px;
}

@media (max-width: 1280px) {
  .assistant-page {
    height: auto;
    min-height: 100vh;
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .chat-pane {
    min-height: 720px;
  }
}

// 移动端整页作为独立全屏房间：固定定位、跟随 visualViewport 高度、底部留出安全区
@include mobile {
  .assistant-page {
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
    background: var(--c-bg-page);
    overflow: hidden;
  }

  .side-pane {
    flex: 0 0 auto;
  }

  .chat-pane {
    flex: 1;
    gap: 10px;
    min-height: 0;
  }

  .chat-pane__back {
    min-height: $touch-target;
    min-width: $touch-target;
    margin-left: -8px;
  }
}
</style>
