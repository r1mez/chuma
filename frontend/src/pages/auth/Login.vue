<template>
  <main class="auth-page">
    <section class="auth-intro">
      <div class="brand"><span><GraduationCap :size="22" /></span>智教慧学</div>
      <div class="intro-copy">
        <p class="eyebrow">AI 教学与学习工作台</p>
        <h1>让知识脉络清晰可见，<br>让每一步学习都有依据。</h1>
        <p>面向计算机科学课程的智能助教助学平台，连接知识图谱、个性化练习与学情分析。</p>
      </div>
      <small>Intelligent Teaching & Learning Workspace</small>
    </section>

    <section class="auth-form-area">
      <form class="login-form" @submit.prevent="handleLogin">
        <header><h2>欢迎回来</h2><p>登录后进入你的专属工作台</p></header>
        <div class="role-tabs">
          <label v-for="item in roles" :key="item.value" :class="{ active: role === item.value }">
            <input v-model="role" type="radio" :value="item.value">{{ item.label }}
          </label>
        </div>
        <label class="field"><span>邮箱</span><input v-model="email" type="email" autocomplete="email" placeholder="请输入邮箱地址" required></label>
        <label class="field"><span>密码</span><input v-model="password" type="password" autocomplete="current-password" placeholder="请输入密码" required></label>
        <div class="form-options"><label><input type="checkbox"> 保持登录</label><a href="#">忘记密码？</a></div>
        <button class="submit" type="submit" :disabled="loading">{{ loading ? '正在登录…' : '登录工作台' }}</button>
        <p class="register-link">还没有账号？<RouterLink to="/register">创建账号</RouterLink></p>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { GraduationCap } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
const router = useRouter()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const role = ref<'student' | 'teacher' | 'admin'>('student')
const loading = ref(false)
const roles = [{ label: '学生', value: 'student' }, { label: '教师', value: 'teacher' }, { label: '管理员', value: 'admin' }] as const
const handleLogin = async () => {
  if (!email.value || !password.value) return ElMessage.warning('请输入邮箱和密码')
  loading.value = true
  try {
    if (role.value === 'admin') {
      if (!email.value.startsWith('admin')) return ElMessage.warning('管理员账号必须以 admin 开头')
      authStore.setToken('admin-mock-token')
      authStore.setUser({ id: 0, name: email.value.split('@')[0], email: email.value, gender: null, stu_level: null, role: 'admin' })
      localStorage.setItem('userRole', 'admin')
      await router.push('/admin/ocr')
      return
    }
    const res: any = await request.post('/auth/login', { email: email.value, password: password.value, user_type: role.value })
    authStore.setToken(res.access_token)
    authStore.setUser({ id: res.user_id, name: res.user_name || email.value.split('@')[0], email: res.user_email || email.value, gender: null, stu_level: res.stu_level ?? null, role: res.user_type })
    localStorage.setItem('userRole', res.user_type)
    ElMessage.success('登录成功')
    await router.push(res.user_type === 'student' ? '/student/dashboard' : '/teacher/dashboard')
  } catch (err: any) { ElMessage.error(err?.response?.data?.detail || '邮箱或密码错误') }
  finally { loading.value = false }
}
</script>

<style scoped>
.auth-page { min-height: 100vh; display: grid; grid-template-columns: minmax(360px, 44%) 1fr; background: #fff; }
.auth-intro { min-height: 100vh; display: flex; flex-direction: column; justify-content: space-between; padding: 42px clamp(36px, 5vw, 82px); color: #fff; background: #10182b; }
.brand { display: flex; align-items: center; gap: 11px; font-size: 17px; font-weight: 700; }
.brand span { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 9px; background: #3159b3; }
.intro-copy { max-width: 590px; }
.eyebrow { margin-bottom: 22px !important; color: #9db1df !important; font-size: 13px; font-weight: 600; letter-spacing: .12em; }
.intro-copy h1 { margin: 0 0 24px; font-size: clamp(34px, 3.2vw, 54px); line-height: 1.25; letter-spacing: -.04em; }
.intro-copy p { margin: 0; color: #aeb8cb; font-size: 15px; line-height: 1.9; }
.auth-intro small { color: #69758c; font-size: 11px; letter-spacing: .08em; }
.auth-form-area { display: grid; place-items: center; padding: 48px 24px; background: #f8f9fb; }
.login-form { width: min(100%, 420px); }
.login-form header { margin-bottom: 30px; }
.login-form h2 { margin: 0; color: #101828; font-size: 29px; letter-spacing: -.02em; }
.login-form header p { margin: 9px 0 0; color: #7a8699; font-size: 14px; }
.role-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-bottom: 24px; padding: 4px; border: 1px solid #e1e6ed; border-radius: 9px; background: #eef1f5; }
.role-tabs label { padding: 9px; border-radius: 6px; color: #667085; font-size: 13px; text-align: center; cursor: pointer; }
.role-tabs label.active { color: #172033; background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.05); font-weight: 600; }
.role-tabs input { display: none; }
.field { display: flex; flex-direction: column; gap: 8px; margin-bottom: 18px; color: #344054; font-size: 13px; font-weight: 600; }
.field input { height: 44px; padding: 0 13px; border: 1px solid #d9e0e9; border-radius: 7px; outline: none; color: #172033; background: #fff; font-weight: 400; }
.field input:focus { border-color: #21469b; box-shadow: 0 0 0 3px rgba(33,70,155,.09); }
.form-options { display: flex; justify-content: space-between; margin: 4px 0 24px; color: #667085; font-size: 12px; }
.form-options a, .register-link a { color: #21469b; text-decoration: none; font-weight: 600; }
.submit { width: 100%; height: 44px; border: 0; border-radius: 7px; color: #fff; background: #21469b; font-weight: 600; cursor: pointer; }
.submit:hover { background: #193a86; }
.submit:disabled { opacity: .6; cursor: wait; }
.register-link { margin: 22px 0 0; color: #7a8699; font-size: 13px; text-align: center; }
@media (max-width: 800px) { .auth-page { grid-template-columns: 1fr; } .auth-intro { min-height: 250px; padding: 28px; } .intro-copy h1 { font-size: 30px; } .intro-copy > p:not(.eyebrow), .auth-intro small { display: none; } }
</style>
