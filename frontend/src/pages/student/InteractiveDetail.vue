<template>
  <BorderGlow class="interactive-detail-page" background-color="transparent">
    <div class="glass-card page-container">
      <!-- 顶部返回与标题 -->
      <div class="header-actions">
        <el-button link @click="goBack" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回互动专区
        </el-button>
        <h2 class="page-title">互动详情</h2>
      </div>

      <!-- 上半部分：问题区 -->
      <div class="section-container question-section">
        <h3 class="section-title">问题区:</h3>
        <div class="scroll-area">
          <div class="post-content">
            <p><strong>学生A:</strong> 问题、对话、描述等占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位。。。。</p>
            <!-- 增加一些占位文本以测试滚动 -->
            <p v-for="i in 5" :key="'q-'+i" class="mock-text">
              这是一段用于测试问题区独立滚动条是否生效的长文本占位 {{ i }}。
            </p>
          </div>
          <div class="spacer"></div>
        </div>
      </div>

      <!-- 分割线 -->
      <div class="divider"></div>

      <!-- 下半部分：答疑区 -->
      <div class="section-container answer-section">
        <h3 class="section-title">答疑区:</h3>
        <div class="scroll-area">
          <div class="reply-list">
            <div class="reply-item">
              <p><strong>老师:</strong> 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位。。。。</p>
            </div>
            <div class="reply-item">
              <p><strong>学生B:</strong> 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位 占位。。。。</p>
            </div>
            
            <!-- 增加一些占位回复以测试滚动 -->
            <div v-for="i in 10" :key="'a-'+i" class="reply-item mock-item">
              <p><strong>学生{{ i }}:</strong> 这是一段用于测试答疑区独立滚动条是否生效的长文本占位回答 {{ i }}。</p>
            </div>
          </div>
          <div class="spacer"></div>
        </div>
      </div>

    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import BorderGlow from '@/components/BorderGlow.vue'

const router = useRouter()

const goBack = () => {
  router.push('/student/interactive')
}
</script>

<style scoped>
.interactive-detail-page {
  color: #000;
  height: calc(100vh - 170px);
  margin: 20px;
}

.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #e5e8e4;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.header-actions {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
  position: relative;
}

.back-btn {
  color: #000;
  font-weight: bold;
  font-size: 1rem;
  position: absolute;
  left: 0;
}

.back-btn:hover {
  color: #2980b9;
}

.page-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: bold;
  color: #000;
  width: 100%;
  text-align: center;
}

/* 区域容器 */
.section-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 保证内部滚动 */
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 1.1rem;
  font-weight: 600;
  flex-shrink: 0;
}

.divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.1);
  margin: 16px 0;
  flex-shrink: 0;
}

/* 滚动区域通用样式 (完全独立，互不影响) */
.scroll-area {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

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

.spacer {
  height: 16px;
}

/* 内容细节 */
.post-content, .reply-item {
  line-height: 1.6;
  font-size: 1rem;
}

.reply-item {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.1);
}

.reply-item:last-child {
  border-bottom: none;
}

.mock-text, .mock-item p {
  color: #555;
}
</style>