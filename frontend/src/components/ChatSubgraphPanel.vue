<template>
  <transition name="slide">
    <div v-if="visible" class="subgraph-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="hit-node-info">
          <span class="hit-node-name">{{ hitNodeName }}</span>
          <el-tag size="small" :color="typeColor" effect="dark" style="margin-left: 8px">
            {{ hitNodeType }}
          </el-tag>
        </div>
        <div class="header-actions">
          <el-button
            v-if="subgraphs && !loading && !error"
            :icon="FullScreen"
            size="small"
            circle
            @click="fullscreenDialogVisible = true"
            class="fullscreen-btn"
            title="全屏查看"
          />
          <el-button
            :icon="Close"
            size="small"
            circle
            @click="$emit('close')"
            class="close-btn"
          />
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="panel-body">
        <el-skeleton :rows="6" animated />
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="panel-body error-state">
        <el-icon :size="32" color="#f56c6c"><WarningFilled /></el-icon>
        <p>{{ error }}</p>
        <el-button size="small" @click="$emit('retry')">重试</el-button>
      </div>

      <!-- Subgraphs content -->
      <div v-else-if="subgraphs" class="panel-body">
        <!-- Upstream subgraph -->
        <div class="subgraph-section">
          <h4 class="section-title">前置知识（上游）</h4>
          <div v-if="subgraphs.upstream.nodes.length > 0" class="chart-container">
            <SubgraphChart
              :nodes="subgraphs.upstream.nodes"
              :edges="subgraphs.upstream.edges"
              :hit-node-id="subgraphs.hitNode.id"
              direction="upstream"
              @node-click="onNodeClick"
            />
          </div>
          <div v-else class="empty-subgraph">
            <el-icon :size="20" color="#c0c4cc"><InfoFilled /></el-icon>
            <span>暂无前置知识</span>
          </div>
        </div>

        <!-- Downstream subgraph -->
        <div class="subgraph-section">
          <h4 class="section-title">后继知识（下游）</h4>
          <div v-if="subgraphs.downstream.nodes.length > 0" class="chart-container">
            <SubgraphChart
              :nodes="subgraphs.downstream.nodes"
              :edges="subgraphs.downstream.edges"
              :hit-node-id="subgraphs.hitNode.id"
              direction="downstream"
              @node-click="onNodeClick"
            />
          </div>
          <div v-else class="empty-subgraph">
            <el-icon :size="20" color="#c0c4cc"><InfoFilled /></el-icon>
            <span>暂无后继知识</span>
          </div>
        </div>

        <!-- Node detail -->
        <div v-if="selectedDetail" class="detail-section">
          <h4 class="section-title">{{ selectedDetail.name }}</h4>
          <el-tag size="small" effect="plain">{{ selectedDetail.type }}</el-tag>
          <p class="detail-desc">{{ selectedDetail.description }}</p>
          <p class="detail-meta">度数: {{ selectedDetail.degree }}</p>
        </div>
      </div>
    </div>
  </transition>

  <!-- 全屏模态框 -->
  <el-dialog
    v-model="fullscreenDialogVisible"
    fullscreen
    :show-close="false"
    class="subgraph-fullscreen-dialog"
    destroy-on-close
  >
    <div class="fullscreen-content">
      <!-- Header -->
      <div class="fullscreen-header">
        <div class="fullscreen-hit-info">
          <span class="fullscreen-hit-name">{{ hitNodeName }}</span>
          <el-tag size="small" :color="typeColor" effect="dark" style="margin-left: 8px">
            {{ hitNodeType }}
          </el-tag>
        </div>
        <el-button
          :icon="Close"
          size="small"
          circle
          @click="fullscreenDialogVisible = false"
          class="fullscreen-close-btn"
        />
      </div>

      <!-- Body: 左右两栏 -->
      <div v-if="subgraphs" class="fullscreen-body">
        <!-- 上游子图 -->
        <div class="fullscreen-chart-section">
          <h4 class="fullscreen-section-title">前置知识（上游）</h4>
          <div v-if="subgraphs.upstream.nodes.length > 0" class="fullscreen-chart-container">
            <SubgraphChart
              :nodes="subgraphs.upstream.nodes"
              :edges="subgraphs.upstream.edges"
              :hit-node-id="subgraphs.hitNode.id"
              direction="upstream"
              :roam="true"
              :fullscreen="true"
              @node-click="onNodeClick"
            />
          </div>
          <div v-else class="empty-subgraph fullscreen-empty">
            <el-icon :size="24" color="#c0c4cc"><InfoFilled /></el-icon>
            <span>暂无前置知识</span>
          </div>
        </div>

        <!-- 下游子图 -->
        <div class="fullscreen-chart-section">
          <h4 class="fullscreen-section-title">后继知识（下游）</h4>
          <div v-if="subgraphs.downstream.nodes.length > 0" class="fullscreen-chart-container">
            <SubgraphChart
              :nodes="subgraphs.downstream.nodes"
              :edges="subgraphs.downstream.edges"
              :hit-node-id="subgraphs.hitNode.id"
              direction="downstream"
              :roam="true"
              :fullscreen="true"
              @node-click="onNodeClick"
            />
          </div>
          <div v-else class="empty-subgraph fullscreen-empty">
            <el-icon :size="24" color="#c0c4cc"><InfoFilled /></el-icon>
            <span>暂无后继知识</span>
          </div>
        </div>
      </div>

      <!-- Footer: 节点详情 -->
      <div v-if="selectedDetail" class="fullscreen-detail">
        <h4 class="fullscreen-section-title">{{ selectedDetail.name }}</h4>
        <el-tag size="small" effect="plain">{{ selectedDetail.type }}</el-tag>
        <p class="fullscreen-detail-desc">{{ selectedDetail.description }}</p>
        <p class="fullscreen-detail-meta">度数: {{ selectedDetail.degree }}</p>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Close, WarningFilled, InfoFilled, FullScreen } from '@element-plus/icons-vue'
import SubgraphChart from '@/components/SubgraphChart.vue'
import type { DirectionalSubgraphs } from '@/composables/useSubgraph'
import type { GraphNode } from '@/api/knowledge'
import { TYPE_COLORS } from '@/constants/knowledgeColors'

const props = defineProps<{
  visible: boolean
  hitNodeName: string
  hitNodeType: string
  subgraphs: DirectionalSubgraphs | null
  loading: boolean
  error: string | null
}>()

defineEmits<{
  close: []
  retry: []
}>()

const selectedDetail = ref<GraphNode | null>(null)
const fullscreenDialogVisible = ref(false)

const typeColor = computed(() => TYPE_COLORS[props.hitNodeType] || '#94A3B8')

function onNodeClick(node: GraphNode) {
  selectedDetail.value = node
}

// Auto-select hit node when subgraphs arrive
watch(() => props.subgraphs, (sg) => {
  if (sg) {
    selectedDetail.value = sg.hitNode
  }
}, { immediate: true })
</script>

<style scoped>
.subgraph-panel {
  width: 35%;
  min-width: 280px;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-left: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}
.slide-enter-from, .slide-leave-to {
  width: 0;
  min-width: 0;
  opacity: 0;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.hit-node-info {
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 4px;
  align-items: center;
}

.hit-node-name {
  font-size: 16px;
  font-weight: 600;
  color: #FF8C00;
}

.panel-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow-y: auto;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #f56c6c;
  text-align: center;
}

.subgraph-section {
  margin-bottom: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 8px 0;
}

.chart-container {
  height: 40%;
  min-height: 160px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.02);
}

.empty-subgraph {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #9ca3af;
  font-size: 13px;
  padding: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.02);
}

.detail-section {
  margin-top: 8px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
}

.detail-desc {
  font-size: 13px;
  color: #4b5563;
  margin: 8px 0 4px;
  line-height: 1.5;
}

.detail-meta {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
}

/* 全屏模态框样式 */
.fullscreen-content {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1a1a2e;
  color: #e0e0e0;
  padding: 16px 24px;
}

.fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.fullscreen-hit-info {
  display: flex;
  align-items: center;
}

.fullscreen-hit-name {
  font-size: 20px;
  font-weight: 700;
  color: #FF8C00;
}

.fullscreen-close-btn {
  color: #e0e0e0;
}

.fullscreen-body {
  flex: 1;
  display: flex;
  flex-direction: row;
  gap: 16px;
  padding: 16px 0;
  min-height: 0;
}

.fullscreen-chart-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.fullscreen-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
  margin: 0 0 12px 0;
}

.fullscreen-chart-container {
  flex: 1;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  min-height: 300px;
}

.fullscreen-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 15px;
}

.fullscreen-detail {
  padding: 16px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  margin-top: 12px;
}

.fullscreen-detail-desc {
  font-size: 14px;
  color: #b0b0b0;
  margin: 8px 0 4px;
  line-height: 1.6;
}

.fullscreen-detail-meta {
  font-size: 12px;
  color: #787878;
  margin: 0;
}
</style>
