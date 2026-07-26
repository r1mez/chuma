<template>
  <BorderGlow class="practice-home-page" background-color="transparent">
    <div class="glass-card page-container">
      <h2 class="page-title">题目练习功能</h2>
      
      <div class="grid-container">
        <div 
          v-for="module in practiceModules" 
          :key="module.id" 
          class="module-card glass-card"
          @click="navigateToPanel(module.id)"
        >
          <span class="module-name">{{ module.name }}</span>
        </div>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import BorderGlow from '@/components/BorderGlow.vue'

const router = useRouter()

const practiceModules = [
  { id: 'ds', name: '数据结构' },
  { id: 'co', name: '计算机组成原理' },
  { id: 'exam', name: '作业与考试' },
  { id: 'os', name: '操作系统' },
  { id: 'net', name: '计算机网络' },
  { id: 'special', name: '专项练习' }
]

const navigateToPanel = (moduleId: string) => {
  router.push({
    path: '/student/practice/panel',
    query: { module: moduleId }
  })
}
</script>

<style scoped>
.practice-home-page {
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
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.page-title {
  margin: 0 0 24px 0;
  font-size: 1.2rem;
  font-weight: bold;
  color: #000;
  flex-shrink: 0;
}

.grid-container {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 32px;
  padding: 0 20px 20px 20px;
}

.module-card {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.8);
  border-color: rgba(0, 0, 0, 0.2);
}

.module-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: #333;
  text-align: center;
}
</style>