<template>
  <BorderGlow class="dashboard-page" background-color="transparent">
    <div class="dashboard-layout">
      <!-- 左侧面板：个人信息与建议 -->
      <div class="left-panel">
        <!-- 个人信息 -->
        <div class="glass-card personal-info">
          <div class="card-header-row">
            <h3 class="card-title">个人信息</h3>
            <el-button type="primary" size="small" :icon="Edit" @click="openEditDialog">编辑个人信息</el-button>
          </div>
          <div class="info-content">
            <div class="avatar-placeholder">{{ genderAvatar }}</div>
            <div class="info-text">
              <p><strong>姓名：</strong>{{ userName }}</p>
              <p><strong>Email：</strong>{{ userEmail }}</p>
              <p><strong>座右铭：</strong>{{ motto || '还没有设置座右铭' }}</p>
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
            <!-- 进度条 (基于进度动态定位) -->
            <div class="progress-bar" :style="{ left: `calc(${subject.progress}% - 12px)` }">
              🚀
            </div>
          </div>

          <!-- 最新与做题记录跳转列表 -->
          <div class="action-list">
            <div class="action-item">
              <span class="action-desc text-truncate">{{ subject.latestMsg }}</span>
              <!-- 跳转到 题目练习面板 -->
              <el-button size="small" type="primary" plain @click="navigateTo('/student/practice/panel', subject.id)">跳转练习</el-button>
            </div>
            <div class="action-item">
              <span class="action-desc text-truncate">{{ subject.recordMsg }}</span>
              <!-- 跳转到 做题记录 -->
              <el-button size="small" type="warning" plain @click="navigateTo('/student/exercise-records', subject.id)">做题记录</el-button>
            </div>
          </div>

          <!-- 知识图谱全宽按钮 -->
          <el-button class="full-width-btn" type="success" plain @click="navigateTo('/student/knowledge', subject.id)">
            {{ subject.name }} 知识图谱
          </el-button>
        </div>
      </div>
    </div>

    <!-- 编辑个人信息弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑个人信息"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="editForm" label-width="80px" class="edit-form">
        <el-form-item label="姓名">
          <el-input v-model="editForm.stu_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.stu_email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="editForm.stu_gender" placeholder="请选择性别" style="width: 100%">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
            <el-option label="保密" value="保密" />
          </el-select>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="editForm.stu_pwd" type="password" placeholder="留空则不修改密码" show-password />
        </el-form-item>
        <el-form-item label="座右铭">
          <el-input
            v-model="editForm.motto"
            type="textarea"
            :rows="2"
            placeholder="请输入您的座右铭"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSaveProfile">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import BorderGlow from '@/components/BorderGlow.vue'
import { fetchCourses, type Course } from '@/api/practice'
import { fetchCurrentUser, updateProfile } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// ========== 个人信息（从数据库/Store 获取） ==========
const userName = ref('加载中...')
const userEmail = ref('')
const userGender = ref<string | null>(null)

// 座右铭仅存前端 localStorage，不从数据库获取
const MOTTO_KEY = 'chuma_user_motto'
const motto = ref(localStorage.getItem(MOTTO_KEY) || '')

// 头像根据性别显示
const genderAvatar = computed(() => {
  if (userGender.value === '女') return '👩'
  if (userGender.value === '男') return '👨'
  return '🧑'
})

/** 加载当前用户信息 */
const loadUserInfo = async () => {
  // 优先使用 Store 中已缓存的信息
  if (authStore.user && authStore.user.name) {
    userName.value = authStore.user.name
    userEmail.value = authStore.user.email || ''
    userGender.value = authStore.user.gender
    return
  }

  // Store 无数据则从服务端获取
  try {
    const me = await fetchCurrentUser()
    userName.value = me.name || '未知用户'
    userEmail.value = me.email || ''
    userGender.value = me.gender || null
    // 同步到 Store
    authStore.setUser({
      id: me.id,
      name: me.name,
      email: me.email,
      gender: me.gender,
      role: me.user_type as 'student' | 'teacher',
    })
  } catch {
    // 降级使用 Store 中的已有信息
    if (authStore.user) {
      userName.value = authStore.user.name
      userEmail.value = authStore.user.email || ''
      userGender.value = authStore.user.gender
    }
  }
}

// ========== 编辑弹窗 ==========
const editDialogVisible = ref(false)
const saving = ref(false)

const editForm = ref({
  stu_name: '',
  stu_email: '',
  stu_gender: '',
  stu_pwd: '',
  motto: '',
})

const openEditDialog = () => {
  editForm.value = {
    stu_name: userName.value === '加载中...' ? '' : userName.value,
    stu_email: userEmail.value,
    stu_gender: userGender.value || '',
    stu_pwd: '',
    motto: motto.value,
  }
  editDialogVisible.value = true
}

const handleSaveProfile = async () => {
  saving.value = true
  try {
    // 1. 保存数据库字段（姓名、邮箱、性别、密码）到后端
    const updateData: Record<string, string> = {}
    if (editForm.value.stu_name) updateData.stu_name = editForm.value.stu_name
    if (editForm.value.stu_email) updateData.stu_email = editForm.value.stu_email
    if (editForm.value.stu_gender) updateData.stu_gender = editForm.value.stu_gender
    if (editForm.value.stu_pwd) updateData.stu_pwd = editForm.value.stu_pwd

    if (Object.keys(updateData).length > 0) {
      await updateProfile(updateData)
    }

    // 2. 保存座右铭到 localStorage（仅前端）
    localStorage.setItem(MOTTO_KEY, editForm.value.motto)
    motto.value = editForm.value.motto

    // 3. 更新页面显示和 Store
    userName.value = editForm.value.stu_name || userName.value
    userEmail.value = editForm.value.stu_email || userEmail.value
    userGender.value = editForm.value.stu_gender || userGender.value

    if (authStore.user) {
      authStore.setUser({
        ...authStore.user,
        name: userName.value,
        email: userEmail.value,
        gender: userGender.value,
      })
    }

    editDialogVisible.value = false
    ElMessage.success('个人信息已保存')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || '保存失败，请重试'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

// ========== 学科卡片数据 ==========
const subjects = ref<Array<{
  id: number
  name: string
  progress: number
  latestMsg: string
  recordMsg: string
}>>([])

// Mock 数据映射：按学科名称匹配进度与消息（后端尚未实现真实数据接口）
const mockSubjectData: Record<string, { progress: number; latestMsg: string; recordMsg: string }> = {
  '数据结构':         { progress: 75, latestMsg: '最新：二叉树非递归遍历', recordMsg: '记录：图的连通性分析' },
  '计算机组成原理':   { progress: 35, latestMsg: '最新：Cache 组相联映射', recordMsg: '记录：浮点数 IEEE754 标准' },
  '操作系统':         { progress: 55, latestMsg: '最新：页面置换算法', recordMsg: '记录：死锁避免与银行家算法' },
  '计算机网络':       { progress: 85, latestMsg: '最新：TCP 拥塞控制状态机', recordMsg: '记录：CIDR 子网划分计算' }
}

onMounted(async () => {
  // 并行加载用户信息和学科列表
  await loadUserInfo()

  try {
    const courses = await fetchCourses()
    if (courses && courses.length > 0) {
      subjects.value = courses.map((course: Course) => {
        const mock = mockSubjectData[course.course_name] || { progress: 0, latestMsg: '暂无记录', recordMsg: '暂无记录' }
        return {
          id: course.course_id,
          name: course.course_name,
          progress: mock.progress,
          latestMsg: mock.latestMsg,
          recordMsg: mock.recordMsg
        }
      })
    } else {
      // 无数据时回退到静态 Mock
      subjects.value = Object.entries(mockSubjectData).map(([name, data], index) => ({
        id: index + 1,
        name,
        ...data
      }))
    }
  } catch (error) {
    console.error('获取学科列表失败:', error)
    ElMessage.error('获取学科列表失败，使用本地数据')
    // 接口失败时回退到静态 Mock
    subjects.value = Object.entries(mockSubjectData).map(([name, data], index) => ({
      id: index + 1,
      name,
      ...data
    }))
  }
})

// 路由跳转逻辑
const navigateTo = (path: string, subjectId?: number | string) => {
  router.push({
    path,
    query: subjectId ? { module: subjectId.toString() } : undefined
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

/* 进度条 */
.progress-bar {
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

/* --- 个人信息卡片标题行 --- */
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-header-row .card-title {
  margin: 0;
}

/* --- 编辑弹窗表单 --- */
.edit-form {
  padding-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
