<template>
  <div class="message" :class="`message--${message.role}`">
    <el-avatar :size="36" class="message__avatar">{{ message.role === 'ai' ? 'AI' : '我' }}</el-avatar>
    <div class="bubble">
      <div class="bubble__meta">
        <strong>{{ message.role === 'ai' ? '简历助手' : '我' }}</strong>
      </div>
      <p class="bubble__text">{{ message.content }}</p>
      <div v-if="message.hint" class="hint">
        <el-icon class="hint__icon"><MagicStick /></el-icon>
        <div>
          <span class="hint__label">引导提示</span>
          <p>{{ message.hint }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { MagicStick } from '@element-plus/icons-vue'

import type { AssistantMessage } from '@/types/resumeAssistant'

defineProps<{
  message: AssistantMessage
}>()
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.message {
  display: flex;
  align-items: flex-start;
  gap: 12px;

  &--user {
    flex-direction: row-reverse;

    .bubble {
      color: var(--c-text-inverse);
      background: var(--c-primary-500);
    }

    .bubble__meta {
      color: rgba(255, 255, 255, 0.82);
    }

    .bubble__text {
      color: inherit;
    }
  }
}

.bubble {
  max-width: min(680px, 78%);
  padding: 14px 16px;
  border-radius: var(--r-md);
  color: var(--c-text-primary);
  background: var(--c-bg-card);
  box-shadow: var(--sh-sm);

  &__meta {
    margin-bottom: 8px;
    color: var(--c-text-tertiary);
    font-size: 12px;
  }

  &__text {
    margin: 0;
    white-space: pre-wrap;
    line-height: 1.7;
    overflow-wrap: anywhere;
  }
}

// 引导提示独立于提问正文，用浅底 + 左侧强调条区分，避免和问题混在一起
.hint {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  border-left: 3px solid var(--c-primary-400);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  background: var(--c-info-light);

  &__icon {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--c-info-text);
  }

  &__label {
    display: block;
    margin-bottom: 4px;
    color: var(--c-info-text);
    font-size: 12px;
    font-weight: var(--fw-semibold);
  }

  p {
    margin: 0;
    color: var(--c-text-secondary);
    font-size: var(--fs-sm);
    line-height: 1.65;
    white-space: pre-wrap;
  }
}

@include mobile {
  .message {
    gap: 8px;
    min-width: 0;
  }

  .bubble {
    max-width: 84%;
    min-width: 0;
    padding: 11px 13px;

    &__text {
      line-height: 1.6;
    }
  }
}
</style>
