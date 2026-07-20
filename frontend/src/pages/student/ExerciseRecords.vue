<template>
  <BorderGlow class="exercise-records-page" background-color="transparent">
    <div class="records-layout">
      <h2 class="page-title">做题记录</h2>
      
      <!-- 四宫格布局 -->
      <div class="grid-container">
        <div v-for="subject in subjects" :key="subject.id" class="glass-card subject-card">
          <!-- 学科头部与进入按钮 -->
          <div class="subject-header">
            <h3 class="subject-title">{{ subject.name }}</h3>
            <el-button 
              size="small" 
              type="primary" 
              plain 
              class="enter-btn"
              @click="enterSubjectDetail(subject.id)"
            >
              进入
            </el-button>
          </div>

          <!-- 最近做题列表 -->
          <div class="records-list scroll-area">
            <div v-for="record in subject.recentRecords" :key="record.id" class="record-item">
              <!-- 题干简述 -->
              <div class="record-stem text-truncate" :title="record.stem">
                {{ record.stem }}
              </div>
              
              <div class="record-meta">
                <!-- 知识点 -->
                <div class="tags">
                  <span v-for="(tag, idx) in record.tags" :key="idx" class="tag">
                    {{ tag }}
                  </span>
                </div>
                <!-- 日期 -->
                <div class="date">{{ record.date }}</div>
              </div>
            </div>
            <!-- 如果题目少于5个，用空条占位以贴合线框图的视觉效果 -->
            <div v-for="i in Math.max(0, 5 - subject.recentRecords.length)" :key="'empty-'+i" class="record-item empty-item"></div>
          </div>
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

// 跳转到该学科的详细记录页面（留白占位页）
const enterSubjectDetail = (subjectId: number) => {
  router.push({
    path: '/student/subject-records',
    query: { subject: subjectId }
  })
}

// Mock 数据：4个学科的近期做题记录
const subjects = ref([
  {
    id: 1,
    name: '数据结构',
    recentRecords: [
      { id: 101, stem: '若一棵二叉树具有10个度为2的结点，则该二叉树的叶子结点个数为？', tags: ['二叉树', '结点计算'], date: '07-20' },
      { id: 102, stem: '在无向图G的邻接矩阵A中，若A[i][j]=1，则A[j][i]等于多少？', tags: ['图', '邻接矩阵'], date: '07-19' },
      { id: 103, stem: '使用迪杰斯特拉(Dijkstra)算法求最短路径的时间复杂度是多少？', tags: ['最短路径', '算法分析'], date: '07-18' }
    ]
  },
  {
    id: 2,
    name: '计算机组成原理',
    recentRecords: [
      { id: 201, stem: 'IEEE 754 单精度浮点数格式中，阶码采用的是什么编码方式？', tags: ['浮点数', 'IEEE 754'], date: '07-20' },
      { id: 202, stem: '在Cache-主存层次结构中，全相联映射的组数是多少？', tags: ['Cache', '映射方式'], date: '07-18' },
      { id: 203, stem: '微程序控制器的控制存储器(CM)主要用于存放什么？', tags: ['控制器', '微程序'], date: '07-17' },
      { id: 204, stem: '指令流水线中可能产生的数据相关有哪些类型？', tags: ['流水线', '数据冲突'], date: '07-15' }
    ]
  },
  {
    id: 3,
    name: '操作系统',
    recentRecords: [
      { id: 301, stem: '产生死锁的四个必要条件是什么？', tags: ['死锁', '必要条件'], date: '07-19' },
      { id: 302, stem: '在虚拟内存管理中，LRU页面置换算法的淘汰原则是什么？', tags: ['虚拟内存', 'LRU算法'], date: '07-19' },
      { id: 303, stem: '进程与线程的根本区别在于？', tags: ['进程', '线程'], date: '07-16' }
    ]
  },
  {
    id: 4,
    name: '计算机网络',
    recentRecords: [
      { id: 401, stem: 'TCP 三次握手中，第二次握手的标志位包含哪些？', tags: ['TCP', '三次握手'], date: '07-20' },
      { id: 402, stem: 'CIDR 地址块 192.168.10.0/20 包含的可用主机地址数是多少？', tags: ['IP地址', 'CIDR'], date: '07-19' },
      { id: 403, stem: '在OSI七层模型中，实现端到端可靠传输的是哪一层？', tags: ['OSI模型', '传输层'], date: '07-18' },
      { id: 404, stem: 'CSMA/CD 协议主要用于哪种类型的网络？', tags: ['数据链路层', '以太网'], date: '07-17' },
      { id: 405, stem: 'DNS 协议主要使用的传输层协议及端口号是什么？', tags: ['DNS', '应用层'], date: '07-16' }
    ]
  }
])
</script>

<style scoped>
.exercise-records-page {
  color: #000;
  height: calc(100vh - 170px);
  margin: 20px;
}

.records-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px 24px;
}

.page-title {
  margin: 0 0 20px 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
}

/* --- 四宫格布局 --- */
.grid-container {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 24px;
  min-height: 0; /* 防止撑开 flex 容器 */
}

/* --- 玻璃拟态卡片 --- */
.glass-card {
  background: #e5e8e4;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 20px;
}

/* 学科头部 */
.subject-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  padding-bottom: 12px;
}

.subject-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: bold;
  color: #c0392b; /* 对应线框图的红色学科名 */
}

.enter-btn {
  border-radius: 6px;
}

/* --- 记录列表与滚动条 --- */
.records-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scroll-area {
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

/* --- 单条记录项 --- */
.record-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid #3498db; /* 对应线框图的蓝色框 */
  border-radius: 6px;
  padding: 8px 12px;
  min-height: 42px; /* 保证空条目的高度一致 */
}

.empty-item {
  border-style: dashed;
  border-color: rgba(52, 152, 219, 0.4);
  background: transparent;
}

.record-stem {
  flex: 1;
  font-size: 0.95rem;
  color: #2c3e50;
  margin-right: 16px;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  font-size: 0.8rem;
  color: #f39c12; /* 对应线框图的黄色/橙色知识点 */
  background: rgba(243, 156, 18, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.date {
  font-size: 0.85rem;
  color: #27ae60; /* 对应线框图的绿色日期 */
  background: rgba(39, 174, 96, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #27ae60; /* 绿色外框 */
}
</style>
