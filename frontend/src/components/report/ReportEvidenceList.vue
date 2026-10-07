<template>
  <el-card shadow="never" class="evidence-card card card--float">
    <template #header><h2>关键问答证据</h2></template>
    <el-empty v-if="evidences.length === 0" description="暂无关键问答证据" />
    <div v-else class="evidences">
      <article v-for="item in evidences" :key="item.title" class="evidence">
        <div class="evidence__header">
          <strong>{{ item.title }}</strong>
          <el-tag :type="getImpactType(item.impact)" effect="light">
            {{ getImpactText(item.impact) }}
          </el-tag>
        </div>
        <p class="weakness">对应结论：{{ item.relatedWeakness }}</p>
        <section>
          <h3>问题</h3>
          <p>{{ item.question }}</p>
        </section>
        <section>
          <h3>回答摘要</h3>
          <p>{{ item.answerSummary }}</p>
        </section>
        <section>
          <h3>为什么作为证据</h3>
          <p>{{ item.evidenceReason }}</p>
        </section>
      </article>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { ReportEvidenceItem } from '@/types/report'

defineProps<{
  evidences: ReportEvidenceItem[]
}>()

const getImpactType = (impact: string) => {
  if (impact === 'high') return 'danger'
  if (impact === 'low') return 'info'
  return 'warning'
}

const getImpactText = (impact: string) => {
  if (impact === 'high') return '高影响'
  if (impact === 'low') return '低影响'
  return '中影响'
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.evidence-card {
  h2 {
    margin: 0;
    font-size: var(--fs-lg);
    font-weight: var(--fw-semibold);
  }
}

.evidences {
  display: grid;
  gap: 14px;
}

.evidence {
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  background: var(--c-bg-card);

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;

    strong {
      color: var(--c-text-primary);
      font-weight: 600;
    }
  }
}

.weakness {
  margin: 8px 0 14px;
  color: var(--c-text-tertiary);
}

section {
  margin-top: 12px;

  h3 {
    margin: 0 0 6px;
    font-size: 14px;
    font-weight: 600;
    color: var(--c-text-secondary);
  }

  p {
    margin: 0;
    color: var(--c-text-secondary);
    line-height: 1.7;
  }
}

@include mobile {
  // 标题与影响标签在窄屏并排会互相顶，允许换行；问答正文来自模型输出，兜住超长 token
  .evidence__header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .evidence {
    padding: 12px;

    strong,
    p {
      overflow-wrap: anywhere;
    }
  }
}
</style>
