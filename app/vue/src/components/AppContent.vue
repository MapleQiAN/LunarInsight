<template>
  <div id="app" class="app-container">
    <router-view />
  </div>
</template>

<script setup>
import { useMessage, useDialog, useNotification } from 'naive-ui'

// 将 Naive UI 的 API 挂载到 window 对象，以便在非组件上下文中使用
window.$message = useMessage()
window.$dialog = useDialog()
window.$notification = useNotification()
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  width: 100%;
}
</style>

