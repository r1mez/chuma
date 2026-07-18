<template>
  <el-container class="student-layout">
    <FloatingLines class="layout-background" />
    <el-aside width="200px" class="student-aside">
      <el-menu router class="student-menu">
        <el-menu-item index="/student/dashboard">学习仪表盘</el-menu-item>
        <el-menu-item index="/student/knowledge">知识图谱</el-menu-item>
        <el-menu-item index="/student/practice">题目练习</el-menu-item>
        <el-menu-item index="/student/wrong-book">错题本</el-menu-item>
        <el-menu-item index="/student/chat">AI 助教</el-menu-item>
        <el-menu-item index="/student/plan">学习计划</el-menu-item>
        <el-menu-item index="/student/ocr">📄 文档解析</el-menu-item>
        <el-menu-item index="/student/kg-pipeline">🧠 图谱构建</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="student-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import FloatingLines from '@/components/FloatingLines.vue'
// 学生侧默认布局
</script>

<style scoped>
.layout-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 0;
  pointer-events: auto; /* Hyperspeed 包含交互动画（点击加速等），需要开启鼠标事件 */
}

.student-layout {
  position: relative;
  min-height: 100vh;
  background-color: transparent;
}

.student-aside {
  position: relative;
  z-index: 10;
  background-color: rgba(255, 255, 255, 0.75) !important;
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(0, 0, 0, 0.05);
}

.student-menu {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item) {
  color: #333 !important;
  border-radius: 8px;
  margin: 4px 8px;
}

:deep(.el-menu-item.is-active),
:deep(.el-menu-item:hover) {
  background-color: rgba(64, 158, 255, 0.15) !important;
  color: #409eff !important;
  font-weight: bold;
}

.student-main {
  position: relative;
  z-index: 10;
  background: transparent;
}

/* 让所有卡片、页面主容器也变成半透明毛玻璃，以便透出背后的特效 */
:deep(.chat-page),
:deep(.kgp-page),
:deep(.ocr-page) {
  background: transparent !important;
}

:deep(.chat-header),
:deep(.chat-messages) {
  background: rgba(255, 255, 255, 0.6) !important;
  backdrop-filter: blur(10px);
}

:deep(.el-card) {
  background: rgba(255, 255, 255, 0.7) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
}
</style>