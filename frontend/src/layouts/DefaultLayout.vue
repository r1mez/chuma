<template>
  <el-container>
    <el-aside width="200px">
      <!-- 学生侧边栏导航 -->
      <el-menu router>
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
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
// 学生侧默认布局
</script>
