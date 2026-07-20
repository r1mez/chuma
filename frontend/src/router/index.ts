import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('@/pages/auth/Login.vue'),
    },
    {
      path: '/register',
      component: () => import('@/pages/auth/Register.vue'),
    },
    {
      path: '/student',
      component: () => import('@/layouts/DefaultLayout.vue'),
      children: [
        { path: 'dashboard', component: () => import('@/pages/student/Dashboard.vue') },
        { path: 'knowledge', component: () => import('@/pages/student/KnowledgeExplore.vue') },
        { path: 'practice', component: () => import('@/pages/student/Practice.vue') },
        { path: 'exercise-records', component: () => import('@/pages/student/ExerciseRecords.vue') },
        { path: 'subject-records', component: () => import('@/pages/student/SubjectRecords.vue') },
        { path: 'chat', component: () => import('@/pages/student/Chat.vue') },
        { path: 'plan', component: () => import('@/pages/student/LearningPlan.vue') },
        { path: 'ocr', component: () => import('@/pages/student/OcrParse.vue') },
        { path: 'kg-pipeline', component: () => import('@/pages/student/KgPipeline.vue') },
      ],
    },
    {
      path: '/teacher',
      component: () => import('@/layouts/TeacherLayout.vue'),
      children: [
        { path: 'courses', component: () => import('@/pages/teacher/CourseManage.vue') },
        { path: 'students', component: () => import('@/pages/teacher/StudentManage.vue') },
        { path: 'analytics', component: () => import('@/pages/teacher/Analytics.vue') },
        { path: 'alerts', component: () => import('@/pages/teacher/Alert.vue') },
        { path: 'assignments', component: () => import('@/pages/teacher/AssignmentGrade.vue') },
      ],
    },
    {
      path: '/',
      redirect: '/login',
    },
  ],
})

export default router
