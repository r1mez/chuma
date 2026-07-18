<template>
  <div class="login-wrapper">
    <!-- Letter Glitch Background -->
    <LetterGlitch class="background-glitch" />

    <!-- Login Form -->
    <div class="form-container">
      <form class="form" @submit.prevent="handleLogin">
        <h2 class="title">智教慧学Agent平台</h2>
        
        <!-- Role Selector -->
        <div class="role-selector">
          <label class="radio-label">
            <input type="radio" v-model="role" value="student" /> Student
          </label>
          <label class="radio-label">
            <input type="radio" v-model="role" value="teacher" /> Teacher
          </label>
        </div>

        <span class="input-span">
          <label for="email" class="label">Email</label>
          <input 
            type="email" 
            name="email" 
            id="email" 
            v-model="email" 
            required 
          />
        </span>
        <span class="input-span">
          <label for="password" class="label">Password</label>
          <input 
            type="password" 
            name="password" 
            id="password" 
            v-model="password" 
            required 
          />
        </span>
        <span class="span"><a href="#">Forgot password?</a></span>
        <input class="submit" type="submit" value="Log in" />
        <span class="span">Don't have an account? <a href="#">Sign up</a></span>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import LetterGlitch from '@/components/LetterGlitch.vue'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const role = ref<'student' | 'teacher'>('student')

const handleLogin = () => {
  if (!email.value || !password.value) {
    ElMessage.warning('Email and Password cannot be empty')
    return
  }

  // 模拟登录，不需要判断密码，只要不为空就可以跳转
  // 伪造一个简单的 token 和 user 存入 store 以保证后续功能正常
  authStore.setToken('mock-token-for-development')
  authStore.user = {
    id: 1,
    name: email.value.split('@')[0],
    role: role.value
  }

  ElMessage.success(`Logged in as ${role.value}`)

  // 根据角色跳转到不同的主页面
  if (role.value === 'student') {
    router.push('/student/chat')
  } else {
    router.push('/teacher/courses')
  }
}
</script>

<style scoped>
.login-wrapper {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background-color: #000;
}

.background-glitch {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.form-container {
  position: relative;
  z-index: 10;
  background: rgba(255, 255, 255, 0.95);
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  width: 500px;
}

.title {
  text-align: center;
  margin-bottom: 1rem;
  color: #333;
  font-size: 2.5rem;
  font-weight: bold;
}

.role-selector {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom:1rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  color: #555;
  font-size: 1.5rem;
}

/* 引入 template.txt 的样式 */
.form {
  --bg-light: #efefef;
  --bg-dark: #707070;
  --clr: #58bc82;
  --clr-alpha: #9c9c9c60;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
  max-width: 500px;
}

.form .input-span {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form input[type="email"],
.form input[type="password"] {
  border-radius: 0.5rem;
  padding: 1rem 0.75rem;
  width: 100%;
  border: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: var(--clr-alpha);
  outline: 2px solid var(--bg-dark);
  box-sizing: border-box;
}

.form input[type="email"]:focus,
.form input[type="password"]:focus {
  outline: 2px solid var(--clr);
}

.label {
  align-self: flex-start;
  color: var(--clr);
  font-weight: 600;
  font-size: 1.2rem;
}

.form .submit {
  padding: 1rem 0.75rem;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 3rem;
  background-color: var(--bg-dark);
  color: var(--bg-light);
  border: none;
  cursor: pointer;
  transition: all 300ms;
  font-weight: 600;
  font-size: 1.2rem;
}

.form .submit:hover {
  background-color: var(--clr);
  color: var(--bg-dark);
}

.span {
  text-decoration: none;
  color: var(--bg-dark);
  font-size: 0.9rem;
}

.span a {
  color: var(--clr);
  font-weight: bold;
}
</style>
