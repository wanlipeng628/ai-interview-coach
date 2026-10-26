<template>
  <footer class="composer">
    <div v-if="errorMessage && !generating" class="composer__error" role="alert">
      <el-icon class="composer__error-icon"><Warning /></el-icon>
      <span class="composer__error-text">{{ errorMessage }}</span>
      <button
        type="button"
        class="composer__error-close"
        aria-label="关闭提示"
        @click="$emit('clearError')"
      >
        <el-icon><Close /></el-icon>
      </button>
    </div>
    <el-input
      ref="textareaRef"
      v-model="draft"
      class="composer__field"
      type="textarea"
      :rows="2"
      resize="none"
      :disabled="disabled"
      placeholder="写下你的回答…"
      @keydown.enter.exact.prevent="handleSend"
    />
    <div class="composer__actions">
      <span class="composer__hint">
        {{ hintText }}
      </span>
      <button type="button" class="composer__finish" :disabled="disabled" @click="$emit('finish')">
        结束面试
      </button>
      <button
        type="button"
        class="composer__send"
        :disabled="disabled || !draft.trim()"
        aria-label="发送回答"
        @click="handleSend"
      >
        <el-icon><Promotion /></el-icon>
      </button>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { Close, Promotion, Warning } from '@element-plus/icons-vue'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  disabled: boolean
  generating: boolean
  errorMessage: string
  failedDraft: string
  /** 流式 stage 事件给出的等待提示 */
  stageLabel?: string
}>()

const emit = defineEmits<{
  send: [answer: string]
  finish: []
  clearError: []
}>()

const draft = ref('')
const textareaRef = ref<InstanceType<typeof import('element-plus')['ElInput']> | null>(null)
const generatingElapsed = ref(0)
let generatingTimer: ReturnType<typeof setInterval> | null = null

const GENERATING_LONG_THRESHOLD = 8

const hintText = computed(() => {
  if (props.generating) {
    // 阶段文案来自后端 stage 事件；超过 8 秒仍没结果就用慢提示兜底
    if (generatingElapsed.value >= GENERATING_LONG_THRESHOLD) {
      return '还在生成，服务繁忙时会自动重试…'
    }
    return props.stageLabel || 'AI 正在出下一题…'
  }
  if (props.errorMessage) {
    return '上次提交失败，回答已保留，可重新发送'
  }
  return '建议：背景 · 方案 · 结果 · 反思'
})

watch(
  () => props.failedDraft,
  (value) => {
    if (value) {
      draft.value = value
      nextTick(() => {
        textareaRef.value?.focus()
      })
    }
  },
)

watch(
  () => props.generating,
  (isGenerating) => {
    if (isGenerating) {
      generatingElapsed.value = 0
      generatingTimer = setInterval(() => {
        generatingElapsed.value += 1
      }, 1000)
    } else {
      if (generatingTimer) {
        clearInterval(generatingTimer)
        generatingTimer = null
      }
      generatingElapsed.value = 0
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (generatingTimer) {
    clearInterval(generatingTimer)
  }
})

const handleSend = () => {
  const answer = draft.value.trim()
  if (!answer) return
  emit('send', answer)
  draft.value = ''
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.composer {
  display: grid;
  gap: 4px;
  margin: 0 4px;
  padding: 10px 12px 10px 18px;
  border-radius: var(--r-pill);
  background: var(--c-chat-surface);
  box-shadow: var(--sh-chat);

  &__error {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    color: var(--c-warning-text);
    font-size: 12px;
    line-height: 1.4;
    background: var(--c-warning-light);
    border-radius: var(--r-sm);

    &-icon {
      flex: none;
      font-size: 14px;
    }

    &-text {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &-close {
      flex: none;
      display: grid;
      place-items: center;
      width: 18px;
      height: 18px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: transparent;
      color: var(--c-warning-text);
      font-size: 12px;
      cursor: pointer;
      opacity: 0.7;
      transition: opacity 0.15s ease;

      &:hover {
        opacity: 1;
      }
    }
  }

  &__field :deep(.el-textarea__inner) {
    min-height: 46px;
    padding: 8px 0 4px;
    border: none;
    background: transparent;
    box-shadow: none;
    color: var(--c-text-primary);
    font-size: 16px;
    line-height: 1.6;

    &::placeholder {
      color: var(--c-chat-quiet);
    }
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  &__hint {
    margin-right: auto;
    color: var(--c-chat-quiet);
    font-size: 12px;
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__finish {
    flex: none;
    height: 32px;
    padding: 0 10px;
    border: none;
    border-radius: var(--r-sm);
    background: transparent;
    color: var(--c-chat-quiet);
    font-size: 13px;
    cursor: pointer;
    transition: color 0.15s ease;

    &:not(:disabled):hover {
      color: var(--c-text-secondary);
    }

    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }

  &__send {
    flex: none;
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border: none;
    border-radius: 50%;
    background: var(--c-chat-ink);
    color: var(--c-text-inverse);
    font-size: 18px;
    cursor: pointer;
    transition:
      transform 0.15s ease,
      opacity 0.15s ease;

    &:not(:disabled):active {
      transform: scale(0.94);
    }

    &:disabled {
      opacity: 0.28;
      cursor: not-allowed;
    }
  }
}

@include mobile {
  .composer {
    margin: 0 10px;
    padding: 8px 10px 8px 16px;

    &__error {
      font-size: 11px;
    }

    &__field :deep(.el-textarea__inner) {
      min-height: 40px;
      font-size: 15px;
    }

    &__hint {
      font-size: 11px;
    }

    &__finish {
      min-height: $touch-target;
    }

    &__send {
      width: $touch-target;
      height: $touch-target;
    }
  }
}
</style>
