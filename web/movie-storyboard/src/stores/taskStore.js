import { defineStore } from 'pinia'
import { io } from 'socket.io-client'
import request from '@/api'
import { ElNotification } from 'element-plus'
import { useProjectStore } from './projectStore'

export const useTaskStore = defineStore('task', {
  state: () => ({
    socket: null,
    taskList: [],
    drawerVisible: false
  }),
  getters: {
    processingCount: (state) => state.taskList.filter(t => t.status === 'processing' || t.status === 'pending').length
  },
  actions: {
    initSocket() {
      if (this.socket) return
      this.socket = io({ 
        transports: ['websocket'], 
        path: '/socket.io' 
      })

      this.socket.on('connect', () => console.log('Socket connected'))
      
      this.socket.on('task_update', (newList) => {
        this.handleTaskUpdate(newList)
      })

      // 初始拉取
      this.fetchTasks()
    },

    async fetchTasks() {
      this.taskList = await request.get('/tasks')
    },

    async clearTask(id) {
      await request.delete(`/tasks/${id}`)
      this.fetchTasks()
    },

    handleTaskUpdate(newList) {
      const projectStore = useProjectStore()
      
      // 检测是否有任务刚完成
      const justFinished = newList.some(newTask => {
        const oldTask = this.taskList.find(t => t.id === newTask.id)
        return oldTask && oldTask.status !== 'success' && newTask.status === 'success'
      })

      this.taskList = newList

      if (justFinished) {
        ElNotification({
          title: '任务完成',
          message: '后台任务已完成，数据已刷新',
          type: 'success',
          position: 'bottom-right'
        })
        
        // 触发当前项目数据的刷新
        // 简单策略：全部刷新，或者根据任务类型细化
        projectStore.refreshCurrentTab() 
      }
    }
  }
})