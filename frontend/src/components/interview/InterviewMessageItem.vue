<template>
  <div class="message" :class="`message--${message.role}`">
    <el-avatar :size="36">{{ message.role === 'ai' ? 'AI' : '我' }}</el-avatar>
    <div class="bubble">
      <div class="bubble__meta">
        <strong>{{ message.role === 'ai' ? 'AI 面试官' : '候选人' }}</strong>
        <span v-if="message.questionNo">Q{{ message.questionNo }}</span>
      </div>
      <p>{{ message.content }}<i v-if="message.streaming" class="cursor" /></p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { InterviewMessage } from '@/types/interview'

defineProps<{
  message: InterviewMessage
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
      color: #fff;
      background: #2f6bff;
    }

    .bubble__meta {
      color: rgba(255, 255, 255, 0.82);
    }
  }
}

.bubble {
  max-width: min(680px, 78%);
  padding: 14px 16px;
  border-radius: 8px;
  color: #101828;
  background: #fff;
  box-shadow: 0 10px 24px rgba(19, 34, 66, 0.06);

  &__meta {
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
    color: #667085;
    font-size: 12px;
  }

  p {
    margin: 0;
    white-space: pre-wrap;
    line-height: 1.7;
  }
}

.cursor {
  display: inline-block;
  width: 2px;
  height: 16px;
  margin-left: 3px;
  vertical-align: text-bottom;
  background: currentColor;
  animation: blink 0.9s infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
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
    line-height: 1.6;

    // 长 URL / 长类名这类不可断行的 token 会把 min-content 撑大，
    // 而消息行同属一个 grid track，一条长 token 会把所有气泡一起撑宽
    p {
      overflow-wrap: anywhere;
    }
  }
}
</style>
