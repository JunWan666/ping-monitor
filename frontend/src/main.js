import { createApp } from 'vue'
import './style.css'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import { installAssetReloadGuard } from './lib/asyncLoader'
import {
  ArrowDown,
  ArrowUp,
  Bell,
  Check,
  CircleCheck,
  CircleCheckFilled,
  CircleCloseFilled,
  CopyDocument,
  DataAnalysis,
  Delete,
  Document,
  Download,
  Lock,
  Monitor,
  Plus,
  Promotion,
  Refresh,
  Search,
  Select,
  Setting,
  SuccessFilled,
  Timer,
  TrendCharts,
  Upload,
  UploadFilled,
  User,
  WarningFilled
} from '@element-plus/icons-vue'

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(registrations => {
    registrations.forEach(registration => {
      registration.unregister()
    })
  })
}

installAssetReloadGuard()

const app = createApp(App)
app.use(router)

const appIcons = {
  ArrowDown,
  ArrowUp,
  Bell,
  Check,
  CircleCheck,
  CircleCheckFilled,
  CircleCloseFilled,
  CopyDocument,
  DataAnalysis,
  Delete,
  Document,
  Download,
  Lock,
  Monitor,
  Plus,
  Promotion,
  Refresh,
  Search,
  Select,
  Setting,
  SuccessFilled,
  Timer,
  TrendCharts,
  Upload,
  UploadFilled,
  User,
  WarningFilled
}

for (const [key, component] of Object.entries(appIcons)) {
  app.component(key, component)
}

app.mount('#app')
