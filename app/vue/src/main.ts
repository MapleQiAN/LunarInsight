import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './styles/main.scss'

const app = createApp(App)

// Create meta tag for naive-ui
const meta = document.createElement('meta')
meta.name = 'naive-ui-style'
document.head.appendChild(meta)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(naive)

app.mount('#app')

