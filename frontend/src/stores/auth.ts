import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<{ id: number; name: string; role: 'student' | 'teacher' | 'admin' } | null>(null)

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUser(newUser: { id: number; name: string; role: 'student' | 'teacher' | 'admin' }) {
    user.value = newUser
    localStorage.setItem('userRole', newUser.role)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userRole')
  }

  return { token, user, setToken, setUser, logout }
})
