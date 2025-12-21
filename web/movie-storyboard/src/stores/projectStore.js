import { defineStore } from 'pinia'
import { getProjectDetail, getCharacters, getShots } from '@/api/project' 

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProjectId: null,
    currentProject: null,
    characterList: [],
    shotList: [],
    // 全局生成配置 (原 genOptions)
    genOptions: {
      imageProviderId: '',
      imageModelName: '',
      textProviderId: '',
      textModelName: '',
      fusionProviderId: '',
      fusionModelName: '',
      videoProviderId: '',
      videoModelName: ''
    },
    loading: {
      project: false,
      shots: false
    }
  }),

  actions: {
    // 初始化项目数据
    async initProject(projectId) {
      this.currentProjectId = projectId
      this.loading.project = true
      try {
        // 并行加载基础信息
        const [projectData, charData] = await Promise.all([
          getProjectDetail(projectId), // 假设 API 封装好了
          getCharacters(projectId)
        ])
        this.currentProject = projectData
        this.characterList = charData
        
        // 恢复本地存储的配置
        const savedOptions = localStorage.getItem('media_gen_options')
        if (savedOptions) {
          this.genOptions = { ...this.genOptions, ...JSON.parse(savedOptions) }
        }
      } catch (error) {
        console.error('Project init failed', error)
      } finally {
        this.loading.project = false
      }
    },

    // 更新配置并持久化
    updateGenOptions(newOptions) {
      this.genOptions = { ...this.genOptions, ...newOptions }
      localStorage.setItem('media_gen_options', JSON.stringify(this.genOptions))
    },

    // 专门加载分镜列表 (因为数据量大，可能单独调用)
    async fetchShots() {
      if (!this.currentProjectId) return
      this.loading.shots = true
      try {
        this.shotList = await getShots(this.currentProjectId)
      } finally {
        this.loading.shots = false
      }
    }
  }
})