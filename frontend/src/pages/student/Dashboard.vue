<template>
  <BorderGlow class="dashboard-page" background-color="transparent">
    <div class="dashboard-layout">
      <!-- 左侧面板：个人信息与建议 -->
      <div class="left-panel">
        <!-- 个人信息 -->
        <div class="glass-card personal-info">
          <h3 class="card-title">个人信息</h3>
          <div class="info-content">
            <div class="avatar-placeholder">🧑‍🎓</div>
            <div class="info-text">
              <p><strong>姓名：</strong>张三</p>
              <p><strong>学号：</strong>2024001</p>
              <p><strong>目标：</strong>408 计算机考研</p>
            </div>
          </div>
        </div>

        <!-- 建议与评估 -->
        <div class="glass-card suggestions">
          <div class="ai-suggestion">
            <h3 class="card-title">AI 助手建议</h3>
            <p class="suggestion-text">当前数据结构进度较好，但计算机组成原理的复习进度稍有落后，建议本周增加对指令系统章节的练习时间。</p>
          </div>
          <div class="divider"></div>
          <div class="teacher-evaluation">
            <h3 class="card-title">老师建议与评估</h3>
            <p class="suggestion-text">基础概念掌握扎实，但在综合应用题上丢分较多，注意知识点之间的串联。</p>
          </div>
        </div>
      </div>

      <!-- 右侧面板：408 考研四宫格学科 -->
      <div class="right-panel">
        <div v-for="subject in subjects" :key="subject.id" class="glass-card subject-card">
          <h3 class="subject-title">{{ subject.name }}</h3>

          <!-- 核心需求：跑道进度条设计 -->
          <div class="runway-container" :title="`掌握度: ${subject.progress}%`">
            <!-- 横线跑道 -->
            <div class="runway-line"></div>
            <!-- 终点红旗 (竖线与旗帜) -->
            <div class="finish-line">
              <div class="flag-pole"></div>
              <div class="flag-cloth"></div>
            </div>
            <!-- 跑步小人 (基于进度动态定位) -->
            <div class="runner" :style="{ left: `calc(${subject.progress}% - 12px)` }">
              🏃
            </div>
          </div>

          <!-- 最新与错题跳转列表 -->
          <div class="action-list">
            <div class="action-item">
              <span class="action-desc text-truncate">{{ subject.latestMsg }}</span>
              <!-- 跳转到 AI 练习 -->
              <el-button size="small" type="primary" plain @click="navigateTo('/student/chat', subject.id)">跳转练习</el-button>
            </div>
            <div class="action-item">
              <span class="action-desc text-truncate">{{ subject.wrongMsg }}</span>
              <!-- 跳转到 错题本 -->
              <el-button size="small" type="danger" plain @click="navigateTo('/student/mistakes', subject.id)">错题回顾</el-button>
            </div>
          </div>

          <!-- 知识图谱全宽按钮 -->
          <el-button class="full-width-btn" type="success" plain @click="navigateTo('/student/graph', subject.id)">
            {{ subject.name }} 知识图谱
          </el-button>
        </div>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import BorderGlow from '@/components/BorderGlow.vue'

const router = useRouter()

// Mock：四个学科的数据，供前端布局展示使用
const subjects = ref([
  { id: 1, name: '数据结构', progress: 75, latestMsg: '最新：二叉树非递归遍历', wrongMsg: '错题：图的连通性分析' },
  { id: 2, name: '计算机组成原理', progress: 35, latestMsg: '最新：Cache 组相联映射', wrongMsg: '错题：浮点数 IEEE754 标准' },
  { id: 3, name: '操作系统', progress: 55, latestMsg: '最新：页面置换算法', wrongMsg: '错题：死锁避免与银行家算法' },
  { id: 4, name: '计算机网络', progress: 85, latestMsg: '最新：TCP 拥塞控制状态机', wrongMsg: '错题：CIDR 子网划分计算' }
])

// 路由跳转逻辑
const navigateTo = (path: string, subjectId?: number) => {
  router.push({
    path,
    query: subjectId ? { subject: subjectId } : undefined
  })
}
</script>

<style scoped>
.dashboard-page {
  color: #000;
  min-height: calc(100vh - 170px);
  margin: 20px;
}

.dashboard-layout {
  display: flex;
  gap: 24px;
  padding: 24px;
  height: 100%;
}

/* 玻璃拟态卡片基础样式，沿用之前配好的 #e5e8e4 */
.glass-card {
  background: #e5e8e4;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
  display: flex;
  flex-direction: column;
}

.card-title {
  margin: 0 0 16px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

/* --- 左侧面板 --- */
.left-panel {
  flex: 0 0 320px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.personal-info .info-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-placeholder {
  font-size: 3rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-text p {
  margin: 8px 0;
  font-size: 0.95rem;
}

.suggestions {
  flex: 1;
}

.suggestion-text {
  font-size: 0.9rem;
  line-height: 1.6;
  color: #444;
  margin: 0;
}

.divider {
  height: 1px;
  background: #c0c5bd;
  margin: 20px 0;
}

/* --- 右侧面板 --- */
.right-panel {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.subject-card {
  justify-content: space-between;
}

.subject-title {
  margin: 0 0 16px 0;
  font-size: 1.2rem;
  color: #2c3e50;
  font-weight: bold;
}

/* --- 核心需求：跑道进度条设计 --- */
.runway-container {
  position: relative;
  height: 40px;
  margin-bottom: 24px;
}

/* 横向的跑道 */
.runway-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: #a3a8a1;
  border-radius: 2px;
}

/* 终点标识容器 */
.finish-line {
  position: absolute;
  right: 0;
  bottom: 0;
  height: 24px;
  width: 20px;
}

/* 终点红色竖线 (旗杆) */
.flag-pole {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 2px;
  height: 24px;
  background-color: #f56c6c;
}

/* 终点红旗 (利用 clip-path 裁切成三角形) */
.flag-cloth {
  position: absolute;
  left: 2px;
  top: 0;
  width: 14px;
  height: 10px;
  background-color: #f56c6c;
  clip-path: polygon(0 0, 100% 50%, 0 100%);
}

/* 跑步的小人 */
.runner {
  position: absolute;
  bottom: 0;
  font-size: 24px;
  line-height: 1;
  /* 平滑动画过渡 */
  transition: left 1s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 2;
  /* 增加立体阴影 */
  filter: drop-shadow(2px 2px 2px rgba(0, 0, 0, 0.2));
}

/* --- 操作列表 --- */
.action-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.action-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.4);
  padding: 8px 12px;
  border-radius: 8px;
}

.action-desc {
  font-size: 0.9rem;
  color: #555;
  flex: 1;
  margin-right: 12px;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.full-width-btn {
  width: 100%;
  margin-top: auto;
}
</style>
