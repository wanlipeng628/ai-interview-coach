<template>
  <div class="message" :class="`message--${message.role}`">
    <div class="bubble" @click="finishTyping">
      <span v-if="message.questionNo && message.role === 'ai'" class="bubble__q">
        Q{{ message.questionNo }}
      </span>
      <p class="bubble__text">{{ revealed }}<i v-if="typing" class="cursor" /></p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { InterviewMessage } from '@/types/interview'

const props = defineProps<{
  message: InterviewMessage
}>()

// 打字机逐字摸高气泡时通知父级：聊天区的滚动往往只看数据变化，
// 看不到子组件内部的高度增长，窄屏上最后几行会落在可视区之外。
const emit = defineEmits<{
  (event: 'grow'): void
}>()

// 题面在服务端已经定稿，这里的打字机只是观感——显示的内容不会在中途改变。
// 用经过时间推导进度（而非每个字排一个 setTimeout）：定时器有最小间隔和调度延迟，
// 逐字排会让长题远远超过目标时长。
const TYPING_TOTAL_MS = 700
const TYPING_MAX_STEP_MS = 20

const typing = ref(false)
const revealed = ref(props.message.content)
let rafId: number | null = null

function stopTyping() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  typing.value = false
}

/** 点一下直接看全文，不让人被动画拖着等 */
function finishTyping() {
  if (!typing.value) return
  stopTyping()
  revealed.value = props.message.content
  emit('grow')
}

function startTyping() {
  const text = props.message.content
  if (!text) return
  // 短题按字数跑，长题封顶 700ms
  const duration = Math.min(TYPING_TOTAL_MS, text.length * TYPING_MAX_STEP_MS)
  const startedAt = performance.now()
  typing.value = true
  revealed.value = ''
  const tick = (now: number) => {
    const ratio = Math.min(1, (now - startedAt) / duration)
    const count = Math.max(1, Math.round(text.length * ratio))
    revealed.value = text.slice(0, count)
    emit('grow')
    if (ratio >= 1) {
      stopTyping()
      return
    }
    rafId = requestAnimationFrame(tick)
  }
  rafId = requestAnimationFrame(tick)
}

onMounted(() => {
  if (!props.message.animate) return
  // 系统开了减少动画就直接给全文
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  startTyping()
})

onBeforeUnmount(stopTyping)
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
