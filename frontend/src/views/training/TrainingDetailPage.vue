<template>
  <div class="detail-page">
    <header class="page-header">
      <div>
        <p>专项训练</p>
        <h1>{{ training.currentTask?.title || '训练详情' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="router.push('/training')">返回列表</el-button>
        <el-button
          :disabled="training.isFinished || !training.currentSessionId"
          type="danger"
          plain
          @click="handleFinish"
        >
          结束训练
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="training.errorMessage"
      :title="training.errorMessage"
      type="error"
      show-icon
      :closable="false"
    />

    <main v-loading="training.loading" class="training-layout">
      <section class="chat-panel">
        <div ref="scrollRef" class="message-list">
          <article
            v-for="message in visibleMessages"
            :key="message.id"
            class="message"
            :class="message.role === 'USER' ? 'message--user' : 'message--ai'"
          >
            <div class="message__role">
              {{ message.role === 'USER' ? '我的回答' : 'AI 训练官' }}
            </div>
            <div class="message__content">{{ message.content }}</div>
          </article>
        </div>

        <div class="answer-box">
          <el-input
            v-model="answer"
            :disabled="training.isFinished"
            type="textarea"
            :rows="5"
            resize="none"
            placeholder="请输入你的回答"
          />
          <div class="answer-actions">
            <span>{{ training.isFinished ? '训练已完成' : '回答后会立即获得反馈和参考要点' }}</span>
            <el-button
              :disabled="training.isFinished || !answer.trim()"
              :loading="training.submitting"
              type="primary"
              @click="handleSubmit"
            >
              提交回答
            </el-button>
          </div>
        </div>
      </section>

      <aside class="side-panel">
        <section class="panel">
          <h2>训练信息</h2>
          <dl>
            <dt>优先级</dt>
            <dd>{{ severityText }}</dd>
            <dt>状态</dt>
            <dd>{{ statusText }}</dd>
            <dt>来源</dt>
            <dd>
              <el-button
                v-if="training.currentTask?.sourceSessionId && training.currentTask.hasReport"
                text
                type="primary"
                @click="handleOpenSourceReport"
              >
                查看来源报告
              </el-button>
              <el-tag v-else-if="training.currentTask?.sourceSessionId" type="info">
                报告不可用
              </el-tag>
              <span v-else>面试报告</span>
            </dd>
          </dl>
          <p>{{ training.currentTask?.reason || '围绕该薄弱点进行问答训练，补齐概念、流程和项目表达。' }}</p>
        </section>

        <section class="panel">
          <h2>本轮反馈</h2>
          <el-empty v-if="!latestReview.feedback" description="提交回答后展示反馈" />
          <template v-else>
            <p>{{ latestReview.feedback }}</p>
            <h3>参考要点</h3>
            <ul>
              <li v-for="point in latestReview.referencePoints" :key="point">{{ point }}</li>
            </ul>
            <h3>参考回答</h3>
            <p>{{ latestReview.sampleAnswer }}</p>
          </template>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useTrainingStore } from '@/stores/training.store'

const route = useRoute()
const router = useRouter()
const training = useTrainingStore()
const answer = ref('')
const scrollRef = ref<HTMLElement | null>(null)

const taskId = computed(() => Number(route.params.taskId))
const visibleMessages = computed(() => training.messages)
const latestReview = computed(() => {
  const reviewed = [...training.messages].reverse().find((item) => item.feedback)
  return {
    feedback: training.latestFeedback || reviewed?.feedback || '',
    referencePoints: training.latestReferencePoints.length
      ? training.latestReferencePoints
      : reviewed?.referencePoints ?? [],
    sampleAnswer: training.latestSampleAnswer || reviewed?.sampleAnswer || '',
  }
})

const severityText = computed(() => {
  if (training.currentTask?.severity === 'High') return '高优先级'
  if (training.currentTask?.severity === 'Low') return '低优先级'
  return '中优先级'
})

const statusText = computed(() => {
  if (training.currentTask?.status === 'DONE') return '已完成'
  if (training.currentTask?.status === 'IN_PROGRESS') return '训练中'
  return '待训练'
})

const handleSubmit = async () => {
  const text = answer.value.trim()
  if (!text) return
  await training.submitTrainingAnswer(text)
  answer.value = ''
  ElMessage.success(training.isFinished ? '训练已完成' : '已生成本轮反馈')
}

const handleFinish = async () => {
  await training.finishTraining()
  ElMessage.success('训练已结束')
}

const handleOpenSourceReport = () => {
  const sessionId = training.currentTask?.sourceSessionId
  if (!sessionId || !training.currentTask?.hasReport) return
  router.push(`/report/${sessionId}`)
}

watch(
  () => training.messages.length,
  async () => {
    await nextTick()
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  },
)

onMounted(async () => {
  if (!Number.isFinite(taskId.value)) {
    router.replace('/training')
    return
  }
  await training.startTraining(taskId.value)
})
</script>

<style scoped lang="scss">
.detail-page {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-radius: 8px;
  background: #fff;

  p {
    margin: 0 0 8px;
    color: #2f6bff;
    font-weight: 800;
  }

  h1 {
    margin: 0;
    font-size: 24px;
  }
}

.header-actions {
  display: flex;
  gap: 10px;
}

.training-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  min-height: 680px;
}

.chat-panel,
.panel {
  border-radius: 8px;
  background: #fff;
}

.chat-panel {
  display: grid;
  grid-template-rows: 1fr auto;
  min-height: 680px;
  overflow: hidden;
}

.message-list {
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 20px;
  overflow-y: auto;
}

.message {
  max-width: 78%;

  &--user {
    justify-self: end;

    .message__content {
      background: #2f6bff;
      color: #fff;
    }
  }

  &--ai .message__content {
    background: #f2f4f7;
    color: #101828;
  }

  &__role {
    margin-bottom: 6px;
    color: #667085;
    font-size: 13px;
  }

  &__content {
    padding: 12px 14px;
    border-radius: 8px;
    line-height: 1.7;
    white-space: pre-wrap;
  }
}

.answer-box {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid #eaecf0;
}

.answer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  color: #667085;
  font-size: 13px;
}

.side-panel {
  display: grid;
  align-content: start;
  gap: 18px;
}

.panel {
  padding: 20px;

  h2 {
    margin: 0 0 16px;
    font-size: 18px;
  }

  h3 {
    margin: 18px 0 8px;
    font-size: 15px;
  }

  p {
    margin: 0;
    color: #475467;
    line-height: 1.7;
  }

  ul {
    display: grid;
    gap: 8px;
    margin: 0;
    padding-left: 18px;
    color: #475467;
    line-height: 1.6;
  }

  dl {
    display: grid;
    grid-template-columns: 72px 1fr;
    gap: 10px;
    margin: 0 0 16px;
  }

  dt {
    color: #98a2b3;
  }

  dd {
    margin: 0;
    color: #101828;
  }
}

@media (max-width: 1080px) {
  .training-layout {
    grid-template-columns: 1fr;
  }
}
</style>
