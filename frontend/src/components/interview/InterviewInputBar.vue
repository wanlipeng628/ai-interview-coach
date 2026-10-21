<template>
  <footer class="composer">
    <el-input
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
        {{ generating ? 'AI 正在出下一题…' : '建议：背景 · 方案 · 结果 · 反思' }}
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
import { Promotion } from '@element-plus/icons-vue'
import { ref } from 'vue'

defineProps<{
  disabled: boolean
  generating: boolean
}>()

const emit = defineEmits<{
  send: [answer: string]
  finish: []
}>()

const draft = ref('')

const handleSend = () => {
  const answer = draft.value.trim()
  if (!answer) return
  emit('send', answer)
  draft.value = ''
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

// 悬浮输入区：房间底部的一块软白胶囊，输入框本身不画边框，只有整块承载阴影
.composer {
  display: grid;
  gap: 4px;
  margin: 0 4px;
  padding: 10px 12px 10px 18px;
  border-radius: var(--r-pill);
  background: var(--c-chat-surface);
  box-shadow: var(--sh-chat);

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

  // 深色圆形发送键：房间里唯一的实心动作
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
