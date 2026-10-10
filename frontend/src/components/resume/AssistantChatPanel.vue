<template>
  <section ref="panelRef" class="chat-panel">
    <el-skeleton v-if="starting && !messages.length" class="chat-panel__skeleton" :rows="4" animated />
    <template v-else>
      <AssistantMessageItem
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
      <div v-if="pending" class="typing">
        <el-avatar :size="36" class="typing__avatar">AI</el-avatar>
        <div class="typing__bubble">
          <span class="typing__dot" />
          <span class="typing__dot" />
          <span class="typing__dot" />
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import AssistantMessageItem from './AssistantMessageItem.vue'
import type { AssistantMessage } from '@/types/resumeAssistant'

const props = defineProps<{
  messages: AssistantMessage[]
  starting: boolean
  pending: boolean
}>()

const panelRef = ref<HTMLElement>()

const scrollToBottom = async () => {
  await nextTick()
  if (!panelRef.value) return
  panelRef.value.scrollTop = panelRef.value.scrollHeight
}

watch(
  () => [props.messages.map((item) => item.content).join('|'), props.pending, props.starting],
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
  border-radius: var(--r-md);
  background: var(--c-bg-tint);
}

.chat-panel__skeleton {
  padding: 4px;
}

.typing {
  display: flex;
  align-items: flex-start;
  gap: 12px;

  &__bubble {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 14px 16px;
    border-radius: var(--r-md);
    background: var(--c-bg-card);
    box-shadow: var(--sh-sm);
  }

  &__dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--c-text-quaternary);
    animation: typing 1.2s infinite ease-in-out;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }

    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

@keyframes typing {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

@include mobile {
  .chat-panel {
    gap: 12px;
    padding: 12px;
  }

  .typing {
    gap: 8px;
  }
}
</style>
