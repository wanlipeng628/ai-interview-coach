<template>
  <section ref="panelRef" class="chat-panel" @scroll.passive="onScroll">
    <InterviewMessageItem
      v-for="message in messages"
      :key="message.id"
      :message="message"
      @grow="followBottom"
    />
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

// 是否贴在底部：只在贴底时跟随新内容；用户往上翻看历史时不拽回去。
// 用滞回区间而不是单一阈值：内容增长的那一瞬间会短暂拉开几十像素，
// 单一阈值会把这个瞬间判成「用户翻走了」，跟随就断了。
const stickToBottom = ref(true)
const STICK_ENTER_PX = 8
const STICK_LEAVE_PX = 120

const onScroll = () => {
  const el = panelRef.value
  if (!el) return
  const gap = el.scrollHeight - el.scrollTop - el.clientHeight
  if (gap <= STICK_ENTER_PX) stickToBottom.value = true
  else if (gap >= STICK_LEAVE_PX) stickToBottom.value = false
  // 中间区域保持原状态：既可能是增长瞬间，也可能是小幅滚动，不为难用户
}

const followBottom = async () => {
  // 等 DOM 更新完再滚：子组件发出 grow 时，气泡高度还没被浏览器重排
  await nextTick()
  const el = panelRef.value
  if (!el || !stickToBottom.value) return
  el.scrollTop = el.scrollHeight
}

const scrollToBottom = async () => {
  await nextTick()
  stickToBottom.value = true
  followBottom()
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
