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
    // 初始化项目 (获取详情 + 分镜 + 角色 + 融图)
    async initProject(projectId) {
      this.currentProjectId = projectId
      this.loading.project = true
      try {
        const [projectData, charData, fusionData, shotData] = await Promise.all([
          getProjectDetail(projectId),
          getCharacters(projectId),
          getFusions(projectId),
          getShots(projectId) // 新增：预加载分镜列表
        ])
        this.currentProject = projectData
        this.characterList = charData || []
        this.fusionList = fusionData || []
        this.shotList = shotData || [] // 赋值
        
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
      } catch (e) { console.error(e) }
    },

    // 单独刷新分镜列表
    async fetchShots() {
      if (!this.currentProjectId) return
      this.loading.shots = true
      try {
        const res = await getShots(this.currentProjectId)
        this.shotList = res || []
      } finally {
        this.loading.shots = false
      }
    },

    // 单独刷新融图列表
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
    },

    // 用于 WebSocket 回调刷新
    refreshCurrentTab() {
      if (!this.currentProjectId) return
      console.log('Auto refreshing all data for project:', this.currentProjectId)
      // 保持数据一致性，建议全部刷新
      this.fetchCharacters()
      this.fetchShots()
      this.fetchFusions()
    }
  }
})