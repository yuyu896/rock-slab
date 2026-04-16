import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
import router from './router'
import { useUserStore } from './store/user'
import { TOKEN_KEY } from './utils/request'
import './styles/variables.css'
import './styles/reset.css'
import './styles/global.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 初始化用户信息：如果有 token 但没有 profile，则获取用户信息
const userStore = useUserStore()
const token = localStorage.getItem(TOKEN_KEY)
if (token && !userStore.profile) {
  userStore.fetchProfile().catch(() => {
    // 获取失败（token 过期等），清除 token
    localStorage.removeItem(TOKEN_KEY)
  })
}

app.mount('#app')
