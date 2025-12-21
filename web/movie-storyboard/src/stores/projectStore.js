import { defineStore } from 'pinia'
import { 
  getProjectDetail, 
  getCharacters, 
  getShots, 
  getFusions
} from '@/api/project' 

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProjectId: null,
    currentProject: null,
    // 列表数据
    characterList: [],
    shotList: [],
    fusionList: [],
    // 全局生成配置
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
    // 加载状态
    loading: {
      project: false,
      shots: false,
      fusions: false
    }
  }),

  actions: {
    // 初始化项目 (获取详情 + 角色 + 融图)
    async initProject(projectId) {
      this.currentProjectId = projectId
      this.loading.project = true
      try {
        // 并行加载基础信息
        const [projectData, charData, fusionData] = await Promise.all([
          getProjectDetail(projectId),
          getCharacters(projectId),
          getFusions(projectId) // 初始加载融图
        ])
        this.currentProject = projectData
        this.characterList = charData || []
        this.fusionList = fusionData || [] // 赋值
        
        // 恢复配置
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

    // 单独刷新角色列表
    async fetchCharacters() {
      if (!this.currentProjectId) return
      try {
        const res = await getCharacters(this.currentProjectId)
        this.characterList = res || []
      } catch (e) {
        console.error(e)
      }
    },

    // 单独刷新分镜列表
    async fetchShots() {
      if (!this.currentProjectId) return
      this.loading.shots = true
      try {
        this.shotList = await getShots(this.currentProjectId)
      } finally {
        this.loading.shots = false
      }
    },

    // 新增：单独刷新融图列表
    async fetchFusions() {
      if (!this.currentProjectId) return
      this.loading.fusions = true
      try {
        this.fusionList = await getFusions(this.currentProjectId)
      } finally {
        this.loading.fusions = false
      }
    },

    updateGenOptions(newOptions) {
      this.genOptions = { ...this.genOptions, ...newOptions }
      localStorage.setItem('media_gen_options', JSON.stringify(this.genOptions))
    }
  }
})