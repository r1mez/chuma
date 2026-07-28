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
        <el-button
          :icon="Close"
          size="small"
          circle
          @click="$emit('close')"
          class="close-btn"
        />
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
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Close, WarningFilled, InfoFilled } from '@element-plus/icons-vue'
import SubgraphChart from '@/components/SubgraphChart.vue'
import type { DirectionalSubgraphs } from '@/composables/useSubgraph'
import type { GraphNode } from '@/api/knowledge'
import { TYPE_COLORS, HIT_NODE_COLOR } from '@/constants/knowledgeColors'

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

.hit-node-name {
  font-size: 16px;
  font-weight: 600;
  color: #FF8C00;
}

.close-btn {
  margin-left: auto;
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
</style>
