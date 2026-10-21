<template>
  <div class="message" :class="`message--${message.role}`">
    <div class="bubble">
      <span v-if="message.questionNo && message.role === 'ai'" class="bubble__q">
        Q{{ message.questionNo }}
      </span>
      <p class="bubble__text">{{ message.content }}<i v-if="message.streaming" class="cursor" /></p>
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

// 房间里的对话规则：不挂头像、不标角色。
// 谁在说话由「位置 + 底色」表达——左侧浅卡是面试官，右侧深色气泡是候选人。
.message {
  display: flex;
  justify-content: flex-start;

  &--user {
    justify-content: flex-end;
  }
}

.bubble {
  max-width: min(660px, 90%);
  padding: 16px 18px;
  border-radius: var(--r-bubble);
  background: var(--c-chat-surface);
  box-shadow: var(--sh-chat);

  &__q {
    display: block;
    margin-bottom: 6px;
    color: var(--c-chat-quiet);
    font-size: var(--fs-xs);
    font-weight: var(--fw-semibold);
    letter-spacing: 0.06em;
  }

  &__text {
    margin: 0;
    color: var(--c-text-primary);
    font-size: 16px;
    line-height: 1.72;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
}

.message--user .bubble {
  max-width: min(560px, 78%);
  padding: 13px 16px;
  background: var(--c-chat-ink);
  box-shadow: none;

  .bubble__text {
    color: var(--c-text-inverse);
    font-size: 15px;
    line-height: 1.66;
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
  .bubble {
    max-width: 88%;
    padding: 14px 16px;

    &__text {
      font-size: 15px;
      line-height: 1.7;
    }
  }

  .message--user .bubble {
    max-width: 84%;
    padding: 11px 14px;
  }
}
</style>
