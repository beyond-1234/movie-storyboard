<template>
  <router-view />
  <!-- 全局任务抽屉 -->
  <TaskDrawer />
</template>

<script setup>
import { onMounted } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import TaskDrawer from '@/components/TaskDrawer.vue'

const taskStore = useTaskStore()

onMounted(() => {
  // 启动 WebSocket 连接
  taskStore.initSocket()
})
</script>

<style>
body {
  margin: 0;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
  background-color: #f0f2f5;
}
</style>