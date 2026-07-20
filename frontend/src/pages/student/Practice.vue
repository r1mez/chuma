<template>
  <BorderGlow class="practice-page" background-color="transparent">
    <div class="practice-layout">
      <!-- 左侧面板：题目与答案 (同一个大框，内部独立滚动) -->
      <div class="left-panel glass-card">
        <!-- 上半部分：题干与答题区 -->
        <div class="section-container">
          <h3 class="title-red">题目题干：</h3>
          <div class="scroll-area">
            <div class="stem-content">{{ question.stem }}</div>
            
            <div class="answer-area">
              <h4 class="title-red answer-title">答题区：</h4>
              
              <!-- 单选题 -->
              <div v-if="question.type === 'single_choice'">
                <el-radio-group v-model="userAnswer" class="custom-radio-group">
                  <el-radio v-for="opt in question.options" :key="opt.label" :value="opt.label">
                    {{ opt.label }}. {{ opt.text }}
                  </el-radio>
                </el-radio-group>
              </div>
              
              <!-- 多选题 -->
              <div v-else-if="question.type === 'multiple_choice'">
                <el-checkbox-group v-model="userAnswerArray" class="custom-checkbox-group">
                  <el-checkbox v-for="opt in question.options" :key="opt.label" :value="opt.label">
                    {{ opt.label }}. {{ opt.text }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              
              <!-- 判断题 -->
              <div v-else-if="question.type === 'true_false'">
                <el-radio-group v-model="userAnswer">
                  <el-radio value="true">正确</el-radio>
                  <el-radio value="false">错误</el-radio>
                </el-radio-group>
              </div>
              
              <!-- 填空/解答题 -->
              <div v-else>
                <el-input
                  v-model="userAnswer"
                  type="textarea"
                  :rows="4"
                  placeholder="请在此输入你的答案（解答题留白区）..."
                  resize="none"
                />
              </div>
            </div>
            <!-- 占位，确保底部不被遮挡 -->
            <div class="spacer"></div>
          </div>
        </div>

        <!-- 红色分割线 -->
        <div class="divider"></div>

        <!-- 下半部分：正确答案与解释 -->
        <div class="section-container">
          <h3 class="title-red">正确答案与解释</h3>
          <div class="scroll-area">
            <div class="explanation-content">
              <p><strong>正确答案：</strong> {{ question.correctAnswer }}</p>
              <p class="mt-2">{{ question.explanation }}</p>
              
              <!-- Mock 大量文本测试独立滚动条 -->
              <p class="mock-text">(以下为测试滚动的占位长文本) <br/> {{ mockLongText }}</p>
            </div>
            <div class="spacer"></div>
          </div>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="right-panel">
        <!-- 上半部分：AI 分析与解惑 -->
        <div class="glass-card flex-card">
          <h3 class="title-blue">ai分析与解惑</h3>
          <div class="scroll-area">
            <div class="ai-content">{{ aiAnalysis }}</div>
            <!-- Mock 测试滚动 -->
            <p class="mock-text">{{ mockLongText }}</p>
            <div class="spacer"></div>
          </div>
        </div>

        <!-- 下半部分：同类型题型列举 -->
        <div class="glass-card flex-card">
          <h3 class="title-green">同类型题型列举</h3>
          <div class="scroll-area">
            <ul class="similar-list">
              <li v-for="sim in similarQuestions" :key="sim.id" class="similar-item">
                <span class="dot"></span>
                <span class="text">{{ sim.title }}</span>
                <el-button size="small" type="success" plain class="go-btn">去练习</el-button>
              </li>
              <!-- Mock 测试滚动 -->
              <li v-for="i in 8" :key="'mock-'+i" class="similar-item mock-item">
                <span class="dot"></span>
                <span class="text">占位同类拓展题目 {{ i }} ...</span>
              </li>
            </ul>
            <div class="spacer"></div>
          </div>
        </div>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import BorderGlow from '@/components/BorderGlow.vue'

// -----------------
// Mock 业务数据
// -----------------
const question = ref({
  type: 'single_choice', // 可切换为: 'multiple_choice', 'true_false', 'essay'
  stem: '在操作系统中，下列哪一种调度算法可能会导致“饥饿”现象？\n\nA. 先来先服务（FCFS）\nB. 时间片轮转（RR）\nC. 最短作业优先（SJF）\nD. 多级反馈队列',
  options: [
    { label: 'A', text: '先来先服务（FCFS）' },
    { label: 'B', text: '时间片轮转（RR）' },
    { label: 'C', text: '最短作业优先（SJF）' },
    { label: 'D', text: '多级反馈队列' }
  ],
  correctAnswer: 'C',
  explanation: '最短作业优先（SJF）算法会优先调度执行时间最短的进程。如果系统中不断有短作业到达，长作业将永远得不到调度，从而产生“饥饿”现象。FCFS、RR、多级反馈队列通常不会导致长作业饥饿。'
})

const aiAnalysis = ref('根据你的做题历史，你在“进程调度算法”这一知识点上经常混淆各个算法的优缺点。\n\nSJF的特点是平均等待时间最短，但致命缺点就是可能导致长作业饥饿。建议结合【操作系统-进程调度】知识图谱，对比记忆FCFS、SJF、RR和多级反馈队列的特点。\n\nAI 分析认为你的基础概念还算清晰，但在处理带有边界条件的综合题时容易忽略“饥饿”这一特殊情况。接下来可以多做一些带有“老化机制”考点的题目。')

const similarQuestions = ref([
  { id: 101, title: '下列哪种调度算法最适合分时操作系统？' },
  { id: 102, title: '关于多级反馈队列调度算法的描述，错误的是？' },
  { id: 103, title: '简述进程调度中“死锁”与“饥饿”的区别。' },
  { id: 104, title: '什么是高响应比优先调度算法？' }
])

const userAnswer = ref('')
const userAnswerArray = ref([])

// 仅用于测试前端独立滚动条是否生效的超长文本
const mockLongText = '这是一段用于测试独立滚动条是否生效的超长占位文本。'.repeat(30)
</script>

<style scoped>
.practice-page {
  color: #000;
  height: calc(100vh - 170px); /* 严格限制高度，防止页面拓展出全局滚动条 */
  margin: 20px;
}

.practice-layout {
  display: flex;
  gap: 24px;
  height: 100%;
  padding: 20px;
}

/* --- 玻璃拟态卡片基础样式 --- */
.glass-card {
  background: #e5e8e4;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

/* --- 左侧面板 --- */
.left-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 保证内部滚动，外部不溢出 */
}

.section-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 限制高度，让内部 scroll-area 滚动 */
  padding: 20px;
}

.divider {
  height: 1px;
  background: #e74c3c; /* 按照线框图，使用红色分割线 */
  margin: 0 20px;
  flex-shrink: 0;
  opacity: 0.5;
}

/* --- 右侧面板 --- */
.right-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow: hidden;
}

.flex-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px;
}

/* --- 标题颜色匹配线框图 --- */
h3 {
  margin: 0 0 12px 0;
  font-size: 1.1rem;
  font-weight: 600;
  flex-shrink: 0; /* 防止标题被挤压 */
}

.title-red {
  color: #c0392b;
}

.title-blue {
  color: #2980b9;
}

.title-green {
  color: #27ae60;
}

/* --- 滚动区域通用样式 (完全独立，互不影响) --- */
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

/* --- 内容区细节样式 --- */
.stem-content {
  font-size: 1rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

.answer-area {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #c0c5bd;
}

.answer-title {
  margin: 0 0 12px 0;
  font-size: 1rem;
  font-weight: 600;
}

.custom-radio-group,
.custom-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}

.explanation-content,
.ai-content {
  line-height: 1.6;
  white-space: pre-wrap;
}

.mock-text {
  margin-top: 16px;
  font-size: 0.85rem;
  color: #7f8c8d;
  line-height: 1.5;
}

/* --- 相似题目列表 --- */
.similar-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.similar-item {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.4);
  padding: 8px 12px;
  border-radius: 8px;
}

.similar-item .dot {
  width: 6px;
  height: 6px;
  background: #27ae60;
  border-radius: 50%;
  margin-right: 12px;
  flex-shrink: 0;
}

.similar-item .text {
  flex: 1;
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.go-btn {
  margin-left: 12px;
}

.mock-item {
  opacity: 0.5;
}
</style>
