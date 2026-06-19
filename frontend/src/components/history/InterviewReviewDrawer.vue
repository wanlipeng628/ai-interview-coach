<template>
  <el-drawer
    :model-value="visible"
    size="58%"
    title="面试详情"
    @close="$emit('close')"
  >
    <el-skeleton v-if="loading" :rows="8" animated />
    <el-empty v-else-if="!review" description="暂无可复盘内容" />
    <div v-else class="review">
      <header class="summary">
        <div>
          <p>面试岗位</p>
          <h2>{{ review.jobRole }}</h2>
        </div>
        <el-tag>{{ review.answeredCount }} 轮回答</el-tag>
      </header>

      <el-empty v-if="review.rounds.length === 0" description="暂无可复盘问答" />
      <el-collapse v-else accordion>
        <el-collapse-item
          v-for="round in review.rounds"
          :key="round.roundNo"
          :name="round.roundNo"
        >
          <template #title>
            <div class="round-title">
              <span>第 {{ round.roundNo }} 轮</span>
              <el-tag :type="getLevelTagType(round.level)" size="small">
                {{ getLevelText(round.level) }}
              </el-tag>
            </div>
          </template>

          <section class="block">
            <h3>AI 问题</h3>
            <p>{{ round.question || '暂无问题记录' }}</p>
          </section>

          <section class="block">
            <h3>你的回答</h3>
            <p>{{ round.answer }}</p>
          </section>

          <section class="block evaluation">
            <h3>AI 评价</h3>
            <p>{{ round.evaluation }}</p>
          </section>

          <section class="block">
            <h3>参考答题要点</h3>
            <ul>
              <li v-for="point in round.referencePoints" :key="point">{{ point }}</li>
            </ul>
          </section>

          <section class="block sample">
            <h3>优秀回答示例</h3>
            <p>{{ round.sampleAnswer }}</p>
          </section>
        </el-collapse-item>
      </el-collapse>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import type { InterviewReview } from '@/types/history'

defineProps<{
  visible: boolean
  loading: boolean
  review: InterviewReview | null
}>()

defineEmits<{
  close: []
}>()

const getLevelTagType = (level: string) => {
  if (level === 'good') return 'success'
  if (level === 'weak') return 'danger'
  return 'warning'
}

const getLevelText = (level: string) => {
  if (level === 'good') return '回答较完整'
  if (level === 'weak') return '需要加强'
  return '可继续完善'
}
</script>

<style scoped lang="scss">
.review {
  display: grid;
  gap: 18px;
}

.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-radius: 8px;
  background: #f5f8ff;

  p {
    margin: 0 0 6px;
    color: #667085;
  }

  h2 {
    margin: 0;
    font-size: 20px;
  }
}

.round-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.block {
  margin-bottom: 16px;

  h3 {
    margin: 0 0 8px;
    font-size: 15px;
  }

  p {
    margin: 0;
    color: #344054;
    line-height: 1.8;
  }

  ul {
    margin: 0;
    padding-left: 18px;
    color: #344054;
    line-height: 1.8;
  }
}

.evaluation,
.sample {
  padding: 12px;
  border-radius: 8px;
  background: #fff7ed;
}
</style>
