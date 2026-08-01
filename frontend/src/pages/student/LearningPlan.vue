<template>
  <BorderGlow class="learning-plan-page" background-color="transparent">
    <div class="page-container glass-card">
      <!-- 顶部标题 -->
      <div class="header">
        <div class="title-badge">{{ studentName }}学生-学习规划</div>
      </div>
      
      <!-- 规划内容大框 -->
      <div class="plan-content-wrapper glass-card">
        <div class="scroll-area">
          <div class="plan-content">
            <!-- 占位内容 -->
            <p class="placeholder-title">规划内容</p>
            <p class="mock-text">{{ mockLongText }}</p>
          </div>
        </div>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import BorderGlow from '@/components/BorderGlow.vue'

// Mock 数据
const studentName = ref('秦诗浩') // 名字与Dashboard中保持一致
const mockLongText = '这是一段用于测试独立滚动条是否生效的超长占位文本。'.repeat(50)
</script>

<style scoped>
.learning-plan-page {
  color: #000;
  height: calc(100vh - 170px);
  margin: 20px;
}

.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  background: #e5e8e4;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.header {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.title-badge {
  font-size: 1.1rem;
  font-weight: 600;
  color: #000;
}

.plan-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.5); /* 内层卡片稍微亮一点 */
  border: 1px solid rgba(0, 0, 0, 0.3); /* 对应线框图内层的边框 */
  border-radius: 8px;
  overflow: hidden; /* 保证内部滚动 */
}

.scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  display: flex;
  flex-direction: column;
}

/* 占位内容样式 */
.plan-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.placeholder-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-top: 40px;
  margin-bottom: 40px;
  color: #333;
}

.mock-text {
  color: #666;
  line-height: 1.8;
  text-align: left;
  width: 100%;
  max-width: 800px; /* 限制一下宽度，让阅读体验更好 */
  margin: 0 auto;
}

/* --- 滚动区域通用样式 --- */
.scroll-area::-webkit-scrollbar {
  width: 6px;
}
.scroll-area::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}
.scroll-area::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}
.scroll-area::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}
</style>