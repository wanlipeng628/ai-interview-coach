<template>
  <section ref="panelRef" class="chat-panel">
    <InterviewMessageItem v-for="message in messages" :key="message.id" :message="message" />
  </section>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import InterviewMessageItem from './InterviewMessageItem.vue'
import type { InterviewMessage } from '@/types/interview'

const props = defineProps<{
  messages: InterviewMessage[]
}>()

const panelRef = ref<HTMLElement>()

const scrollToBottom = async () => {
  await nextTick()
  if (!panelRef.value) return
  panelRef.value.scrollTop = panelRef.value.scrollHeight
}

watch(
  () => props.messages.map((item) => item.content).join('|'),
  scrollToBottom,
  { immediate: true },
)
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

// 对话区不再是一个独立色块：房间底色由页面承担，这里只负责节奏。
.chat-panel {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 16px;
  overflow-y: auto;
  padding: 6px 20px 18px;

  // 桌面端内容列居中并限宽，避免宽屏下每行拉得太长
  > * {
    width: 100%;
    max-width: 760px;
    justify-self: center;
  }
}

@include mobile {
  .chat-panel {
    gap: 14px;
    padding: 4px 14px 14px;
  }
}
</style>
