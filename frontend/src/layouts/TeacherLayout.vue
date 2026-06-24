<template>
  <el-container>
    <el-aside width="200px">
      <!-- 教师侧边栏导航 -->
      <el-menu router>
        <el-menu-item index="/teacher/courses">课程管理</el-menu-item>
        <el-menu-item index="/teacher/students">学生管理</el-menu-item>
        <el-menu-item index="/teacher/analytics">学情报告</el-menu-item>
        <el-menu-item index="/teacher/alerts">预警面板</el-menu-item>
        <el-menu-item index="/teacher/assignments">作业批改</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
// 教师侧默认布局
</script>
