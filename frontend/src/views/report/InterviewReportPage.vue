<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p>面试报告</p>
        <h1>{{ currentTitle }}</h1>
      </div>
      <el-button
        :disabled="!report.currentSessionId"
        :loading="report.generating"
        type="primary"
        @click="handleRegenerate"
      >
        重新生成报告
      </el-button>
    </header>

    <el-alert
      v-if="report.generating"
      title="正在生成面试报告，请稍等..."
      type="info"
      show-icon
      :closable="false"
    />
    <el-alert
      v-if="report.errorMessage"
      :title="report.errorMessage"
      type="error"
      show-icon
      :closable="false"
    />

    <section class="workspace">
      <ReportHistoryList
        :reports="report.reportList"
        :active-session-id="report.currentSessionId"
        :loading="report.loadingList"
        @select="handleSelectReport"
      />

      <main class="detail">
        <el-skeleton v-if="report.loading" :rows="8" animated />
        <el-empty v-else-if="!report.hasReport" description="暂无已生成的面试报告">
          <el-button type="primary" @click="router.push('/mock-interview')">
            去开始一场面试
          </el-button>
        </el-empty>
        <el-empty v-else-if="report.errorMessage && !report.generating" description="报告加载失败">
          <el-button @click="handleReload">重新加载</el-button>
        </el-empty>
        <template v-else>
          <section class="grid">
            <ReportSummaryCard :summary="report.summary" />
            <ChartCard title="能力维度分析">
              <AbilityRadarChart :data="report.abilities" />
            </ChartCard>
          </section>

          <section class="grid">
            <ReportInsightList :insights="report.insights" />
            <TrainingSuggestionList :suggestions="report.suggestions" />
          </section>

          <ReportEvidenceList :evidences="report.evidences" />
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AbilityRadarChart from '@/components/charts/AbilityRadarChart.vue'
import ChartCard from '@/components/dashboard/ChartCard.vue'
import ReportEvidenceList from '@/components/report/ReportEvidenceList.vue'
import ReportHistoryList from '@/components/report/ReportHistoryList.vue'
import ReportInsightList from '@/components/report/ReportInsightList.vue'
import ReportSummaryCard from '@/components/report/ReportSummaryCard.vue'
import TrainingSuggestionList from '@/components/report/TrainingSuggestionList.vue'
import { useReportStore } from '@/stores/report.store'

const report = useReportStore()
const route = useRoute()
const router = useRouter()

const routeSessionId = computed(() => {
  const value = route.params.sessionId
  return typeof value === 'string' ? value : ''
})

const currentTitle = computed(() => {
  const meta = report.currentReportMeta
  return meta ? `${meta.jobRole} 面试分析` : '最近一次面试分析'
})

const handleRegenerate = () => {
  if (report.currentSessionId) {
    report.generateReport(report.currentSessionId)
  }
}

const handleReload = () => {
  if (routeSessionId.value) {
    report.loadOrGenerateReport(routeSessionId.value)
    return
  }
  report.initialize()
}

const handleSelectReport = async (sessionId: string) => {
  if (sessionId === report.currentSessionId) return
  await router.replace({ name: 'InterviewReport', params: { sessionId } })
}

watch(routeSessionId, async (sessionId) => {
  if (sessionId && sessionId !== report.currentSessionId) {
    await report.selectReport(sessionId)
  }
})

onMounted(async () => {
  await report.initialize(routeSessionId.value)
  if (!routeSessionId.value && report.currentSessionId) {
    await router.replace({
      name: 'InterviewReport',
      params: { sessionId: report.currentSessionId },
    })
  }
})
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.page {
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

.workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.detail {
  display: grid;
  gap: 18px;
}

.grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(0, 1.2fr);
  gap: 18px;
}

@media (max-width: 1180px) {
  .workspace,
  .grid {
    grid-template-columns: 1fr;
  }
}

@include mobile {
  .page {
    gap: 12px;
    padding: 14px;
  }

  // 标题与「重新生成报告」按钮并排时在 375px 会顶到边缘，改为纵向堆叠、按钮占满整行
  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 14px;

    > div {
      min-width: 0;
    }

    // h1 由 job_role 拼成，超长英文 token 会顶宽 .page 的 auto 轨道，进而撑出横向滚动条
    h1 {
      font-size: 20px;
      overflow-wrap: anywhere;
    }

    :deep(.el-button) {
      width: 100%;
    }
  }

  // 单列 grid 的列宽是 1fr(=minmax(auto,1fr))，子项 min-content 过宽会顶出横向滚动条
  .workspace,
  .detail,
  .grid {
    gap: 12px;

    > * {
      min-width: 0;
    }
  }

  // 错误/生成中提示的文案来自后端 detail，同样兜住超长 token
  :deep(.el-alert__title),
  :deep(.el-alert__description) {
    overflow-wrap: anywhere;
  }
}
</style>
