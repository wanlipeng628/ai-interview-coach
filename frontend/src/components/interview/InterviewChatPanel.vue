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

.chat-panel {
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 18px;
  overflow-y: auto;
  padding: 20px;
  border-radius: 8px;
  background: #eef3fb;
}

@include mobile {
  .chat-panel {
    gap: 12px;
    padding: 12px;
  }
}
</style>
