<template>
  <div>
    <!-- 悬浮球 -->
    <div class="fixed bottom-8 right-8 z-50 cursor-pointer transition-transform hover:scale-110" @click="store.drawerVisible = true">
      <el-badge :value="store.processingCount" :hidden="store.processingCount === 0">
        <el-button type="primary" plain :icon="store.processingCount > 0 ? 'Loading' : 'Files'" circle size="large" />
      </el-badge>
    </div>

    <el-drawer v-model="store.drawerVisible" title="后台任务队列" size="400px">
      <div v-if="store.taskList.length === 0" class="flex justify-center mt-10 text-gray-400">暂无任务</div>
      <div v-for="task in store.taskList" :key="task.id" class="mb-4 p-3 border rounded shadow-sm bg-white">
        <div class="flex justify-between items-center mb-2">
          <span class="font-bold text-sm truncate w-48">{{ task.desc }}</span>
          <el-tag size="small" :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
        </div>
        <div class="flex justify-between text-xs text-gray-500 mb-2">
          <span>{{ task.created_at }}</span>
          <el-icon v-if="task.status !== 'processing'" class="cursor-pointer hover:text-red-500" @click="store.clearTask(task.id)"><Close /></el-icon>
        </div>
        <el-progress 
          v-if="task.status !== 'pending'" 
          :percentage="task.status === 'success' ? 100 : 50" 
          :status="task.status === 'success' ? 'success' : (task.status === 'failed' ? 'exception' : '')" 
          :show-text="false" 
        />
        <div v-if="task.error" class="text-xs text-red-500 mt-2 bg-red-50 p-1 rounded">{{ task.error }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { useTaskStore } from '@/stores/taskStore'

const store = useTaskStore()

const getStatusType = (s) => ({ success: 'success', failed: 'danger', processing: 'primary', pending: 'info' }[s])
const getStatusText = (s) => ({ pending: '排队中', processing: '生成中', success: '完成', failed: '失败' }[s] || s)
</script>