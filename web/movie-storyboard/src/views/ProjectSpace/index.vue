<template>
  <div class="project-space h-screen flex flex-col bg-gray-50 overflow-hidden">
    <!-- 1. 顶部导航栏 -->
    <header class="bg-gray-800 text-white h-14 shrink-0 flex justify-between items-center px-4 shadow-md z-20">
      <div class="flex items-center gap-4">
        <router-link 
          to="/series" 
          class="flex items-center gap-1 text-gray-300 hover:text-white transition-colors text-sm border border-gray-600 px-2 py-1 rounded"
        >
          <el-icon><Back /></el-icon> 返回剧集
        </router-link>
        <div class="h-4 w-px bg-gray-600"></div>
        <h1 class="text-base font-bold flex items-center gap-2">
          <el-icon><Film /></el-icon> 电影分镜管理系统
        </h1>
      </div>

      <div class="flex items-center gap-3">
        <!-- 项目切换器 -->
        <el-select 
          v-model="store.currentProjectId" 
          placeholder="切换项目" 
          size="small" 
          class="w-48 !bg-transparent"
          @change="handleProjectSwitch"
        >
          <el-option 
            v-for="p in projectList" 
            :key="p.id" 
            :label="p.film_name" 
            :value="p.id" 
          />
        </el-select>

        <el-button type="primary" size="small" icon="Plus" @click="openCreateProject">新建项目</el-button>
        <el-button type="info" size="small" icon="Operation" @click="settingsVisible = true">模型管理</el-button>
      </div>
    </header>

    <!-- 2. 主内容区域 -->
    <main class="flex-1 flex flex-col min-h-0 p-4 gap-4 overflow-hidden">
      <!-- 2.1 项目信息卡片 (固定高度) -->
      <el-card v-if="store.currentProject" class="shrink-0 project-info-card" :body-style="{ padding: '15px' }">
        <div class="flex justify-between items-start mb-3">
          <div class="flex flex-col gap-1">
            <span class="text-xl font-bold text-gray-800">{{ store.currentProject.film_name }}</span>
            <div class="flex items-center gap-3">
              <el-tag v-if="store.currentProject.script_core_conflict" type="success" size="small"
                style="white-space: pre-wrap; height: auto; text-align: left; padding: 4px 8px;">
                核心冲突: {{ store.currentProject.script_core_conflict }}
              </el-tag>
            </div>
            <div class="text-xs text-gray-500 mt-1 flex gap-4">
               <span>创建时间: {{ formatDate(store.currentProject.created_at) }}</span>
               <span v-if="store.currentProject.script_emotional_keywords">
                 情感基调: {{ store.currentProject.script_emotional_keywords }}
               </span>
            </div>
          </div>

          <!-- 快捷操作栏 -->
          <div class="flex gap-3 text-sm">
            <el-button link type="warning" icon="Film" @click="handleExportJianying">导出剪映草稿</el-button>
            <el-button link type="primary" icon="Edit" @click="openEditProject">编辑详情</el-button>
            <el-button link type="info" icon="View" @click="analysisVisible = true">风格分析</el-button>
            <el-button link type="info" icon="Clock" @click="handleHistory">历史回溯</el-button>
            <el-popconfirm title="确定删除该项目吗?" @confirm="handleDeleteProject">
              <template #reference>
                <el-button link type="danger" icon="Delete">删除项目</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>

        <el-descriptions :column="4" border size="small" class="custom-desc">
          <el-descriptions-item label="基础信息" :span="2">
            <div class="truncate-2" :title="store.currentProject.basic_info">
              {{ store.currentProject.basic_info || '暂无' }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="色彩体系" :span="1">
            <div class="truncate-1" :title="store.currentProject.visual_color_system">
              {{ store.currentProject.visual_color_system || '暂无' }}
            </div>
          </el-descriptions-item>
           <el-descriptions-item label="人物设定" :span="1">
            <div class="truncate-1" :title="store.currentProject.visual_consistency_prompt">
              {{ store.currentProject.visual_consistency_prompt ? '已设置' : '未设置' }}
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 2.2 核心业务 Tabs (自适应高度) -->
      <div class="flex-1 bg-white rounded shadow-sm overflow-hidden flex flex-col relative border border-gray-200">
        <el-tabs v-model="activeTab" class="h-full flex flex-col custom-tabs" @tab-click="handleTabClick">
          
          <el-tab-pane label="角色设定" name="characters" class="h-full overflow-hidden flex flex-col">
            <CharacterTab v-if="isTabMounted('characters')" />
          </el-tab-pane>
          
          <el-tab-pane label="剧本创作" name="script" class="h-full overflow-hidden flex flex-col">
            <ScriptTab v-if="isTabMounted('script')" />
          </el-tab-pane>
          
          <el-tab-pane label="场景列表" name="scenes" class="h-full overflow-hidden flex flex-col">
            <SceneTab v-if="isTabMounted('scenes')" />
          </el-tab-pane>
          
          <el-tab-pane label="融图功能" name="fusion" class="h-full overflow-hidden flex flex-col">
            <FusionTab v-if="isTabMounted('fusion')" />
          </el-tab-pane>

        </el-tabs>
      </div>
    </main>

    <!-- 3. 全局弹窗组件 -->
    <SettingsDialog v-model="settingsVisible" />

    <!-- 3.1 项目编辑弹窗 -->
    <el-dialog 
      v-model="projectDialog.visible" 
      :title="projectDialog.isEdit ? '编辑项目' : '新建项目'" 
      width="600px"
    >
      <el-form :model="projectForm" label-width="100px" class="py-2">
        <el-tabs type="card">
          <el-tab-pane label="基础信息">
            <el-form-item label="项目名称" required>
              <el-input v-model="projectForm.film_name" placeholder="例如：黑神话：悟空" />
            </el-form-item>
            <el-form-item label="核心冲突">
              <el-input v-model="projectForm.script_core_conflict" type="textarea" :rows="3" placeholder="全剧的核心冲突..." />
            </el-form-item>
            <el-form-item label="情感关键词">
              <el-input v-model="projectForm.script_emotional_keywords" placeholder="例如：史诗、悲壮、复仇" />
            </el-form-item>
            <el-form-item label="基础信息">
              <el-input v-model="projectForm.basic_info" type="textarea" :rows="4" placeholder="世界观、时代背景、通用人物小传等..." />
            </el-form-item>
          </el-tab-pane>
          <el-tab-pane label="视觉与设定">
            <el-form-item label="色彩体系">
              <el-input v-model="projectForm.visual_color_system" type="textarea" :rows="3" placeholder="例如：黑金冷色调..." />
            </el-form-item>
            <el-form-item label="人物设定">
              <el-input 
                v-model="projectForm.visual_consistency_prompt" 
                type="textarea" 
                :rows="6" 
                placeholder="用于保持角色一致性的 Prompt，将影响角色列表的自动生成..." 
              />
            </el-form-item>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="projectDialog.visible = false">取消</el-button>
        <el-button type="primary" plain @click="submitProject">确定</el-button>
      </template>
    </el-dialog>

    <!-- 3.2 风格分析弹窗 -->
    <el-dialog v-model="analysisVisible" title="视觉风格分析" width="500px">
      <div class="flex flex-col gap-4">
        <div 
          class="border-2 border-dashed border-gray-300 rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
          @click="$refs.analysisInput.click()"
          @drop.prevent="handleAnalysisDrop" 
          @dragover.prevent
        >
          <img v-if="analysisPreview" :src="analysisPreview" class="max-h-64 object-contain rounded" />
          <div v-else class="text-center text-gray-400">
            <el-icon size="40"><UploadFilled /></el-icon>
            <div class="mt-2">点击或拖拽上传参考图</div>
          </div>
          <input type="file" ref="analysisInput" class="hidden" accept="image/*" @change="handleAnalysisFile" />
        </div>

        <el-button type="primary" :loading="analyzing" :disabled="!analysisFile" @click="startAnalysis">
          开始分析风格
        </el-button>

        <div v-if="analysisResult" class="bg-gray-100 p-3 rounded text-sm relative group">
          <div class="font-bold mb-1 text-gray-700">分析结果：</div>
          <div class="whitespace-pre-wrap text-gray-600">{{ analysisResult }}</div>
          <el-button 
            type="primary" 
            link 
            size="small" 
            icon="CopyDocument" 
            class="absolute top-2 right-2 opacity-0 group-hover:opacity-100"
            @click="copyText(analysisResult)"
          >
            复制
          </el-button>
        </div>
      </div>
    </el-dialog>

<!-- 3.3 历史回溯弹窗 -->
    <HistoryDialog 
      v-model="historyVisible" 
      @restore-success="handleHistoryRestore"
    />

  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projectStore'
import { getProjects, createProject, updateProject, deleteProject, exportJianyingDraft } from '@/api/project'
import { analyzeImage } from '@/api/generation'
import { ElMessage, ElNotification } from 'element-plus'

// 子模块组件
import CharacterTab from './components/CharacterTab/index.vue'
import ScriptTab from './components/ScriptTab/index.vue'
import SceneTab from './components/SceneTab/index.vue'
import FusionTab from './components/FusionTab/index.vue'
import SettingsDialog from './components/SettingsDialog/index.vue'
import HistoryDialog from '@/components/HistoryDialog.vue'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()

// State
const activeTab = ref('characters')
const projectList = ref([])
const settingsVisible = ref(false)
const historyVisible = ref(false)

// 优化 Tab 加载：只挂载已点击过的 Tab，避免初始化过慢
const mountedTabs = ref(new Set(['characters']))

// Project Dialog State
const projectDialog = ref({ visible: false, isEdit: false })
const projectForm = ref({})

// Analysis State
const analysisVisible = ref(false)
const analysisFile = ref(null)
const analysisPreview = ref('')
const analysisResult = ref('')
const analyzing = ref(false)
const analysisInput = ref(null)

// --- Initialization ---

onMounted(async () => {
  // 1. 获取项目列表
  await fetchProjectList()
  
  // 2. 初始化当前项目
  const pid = route.params.id
  if (pid) {
    // 检查项目是否存在
    const exists = projectList.value.find(p => p.id === pid)
    if (exists) {
      store.initProject(pid)
    } else if (projectList.value.length > 0) {
      // 如果 ID 不对，跳转第一个
      handleProjectSwitch(projectList.value[0].id)
    }
  } else if (projectList.value.length > 0) {
    handleProjectSwitch(projectList.value[0].id)
  }
})

// --- Methods: Project Management ---

const fetchProjectList = async () => {
  try {
    const seriesId = route.query.series_id
    projectList.value = await getProjects({ series_id: seriesId })
  } catch (e) {
    console.error(e)
  }
}

const handleProjectSwitch = (id) => {
  router.push({ params: { id }, query: route.query })
  store.initProject(id)
  activeTab.value = 'characters'
  mountedTabs.value = new Set(['characters']) // 重置 Tab 缓存
}

const openCreateProject = () => {
  projectForm.value = {
    film_name: '',
    script_core_conflict: store.currentProject?.script_core_conflict || '',
    basic_info: store.currentProject?.basic_info || '',
    visual_color_system: store.currentProject?.visual_color_system || '',
    series_id: route.query.series_id
  }
  projectDialog.value = { visible: true, isEdit: false }
}

const openEditProject = () => {
  projectForm.value = JSON.parse(JSON.stringify(store.currentProject))
  projectDialog.value = { visible: true, isEdit: true }
}

const submitProject = async () => {
  if (!projectForm.value.film_name) return ElMessage.warning('项目名称必填')
  
  try {
    let res
    if (projectDialog.value.isEdit) {
      res = await updateProject(projectForm.value.id, projectForm.value)
      store.currentProject = res
      // 更新列表中的信息
      const idx = projectList.value.findIndex(p => p.id === res.id)
      if (idx !== -1) projectList.value[idx] = res
      ElMessage.success('更新成功')
    } else {
      res = await createProject(projectForm.value)
      projectList.value.unshift(res)
      handleProjectSwitch(res.id)
      ElMessage.success('创建成功')
    }
    projectDialog.value.visible = false
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteProject = async () => {
  try {
    await deleteProject(store.currentProjectId)
    ElMessage.success('删除成功')
    await fetchProjectList()
    if (projectList.value.length > 0) {
      handleProjectSwitch(projectList.value[0].id)
    } else {
      router.push('/series')
    }
  } catch (e) { console.error(e) }
}

const handleExportJianying = async () => {
  try {
    ElNotification.info({ title: '正在导出', message: '正在打包资源，请稍候...' })
    const blob = await exportJianyingDraft(store.currentProjectId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${store.currentProject.film_name}_draft.zip`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    a.remove()
    ElNotification.success({ title: '导出成功', message: '文件已开始下载' })
  } catch (e) {
    console.error(e)
    ElMessage.error('导出失败')
  }
}

// --- Methods: Tabs ---

const handleTabClick = (tab) => {
  mountedTabs.value.add(tab.paneName)
  // 特定 Tab 的刷新逻辑
  if (tab.paneName === 'scenes') {
    store.fetchShots()
  }
  // Fusion Tab 在其组件 mounted 时会自动 fetch
}

const isTabMounted = (name) => mountedTabs.value.has(name)

// --- Methods: Visual Analysis ---

const handleAnalysisFile = (e) => {
  const file = e.target.files[0]
  if (file) setAnalysisFile(file)
}

const handleAnalysisDrop = (e) => {
  const file = e.dataTransfer.files[0]
  if (file) setAnalysisFile(file)
}

const setAnalysisFile = (file) => {
  if (!file.type.startsWith('image/')) return ElMessage.warning('请上传图片')
  analysisFile.value = file
  analysisPreview.value = URL.createObjectURL(file)
  analysisResult.value = ''
}

const startAnalysis = async () => {
  analyzing.value = true
  try {
    const res = await analyzeImage(analysisFile.value)
    if (res.success) {
      analysisResult.value = res.style_description
    } else {
      ElMessage.error(res.error || '分析失败')
    }
  } catch (e) {
    console.error(e)
  } finally {
    analyzing.value = false
  }
}

// --- Utils ---

const formatDate = (str) => {
  if (!str) return ''
  return new Date(str).toLocaleDateString()
}

const copyText = (text) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制')
}

const handleHistory = () => {
  historyVisible.value = true
}

// 新增：处理历史恢复后的刷新逻辑
const handleHistoryRestore = (type) => {
  console.log('History restore triggered for:', type)
  
  if (type === 'character') {
    store.fetchCharacters() // 刷新角色列表
  } else if (type === 'shot') {
    store.fetchShots() // 刷新场景列表
  } else if (type === 'fusion') {
    store.fetchFusions() // 刷新融图列表
  }
}

</script>

<style scoped>
/* 深度调整 Element Plus Tabs 样式以适应 Flex 布局 */
.custom-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.custom-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  background-color: #fafafa;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 15px;
}
.custom-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.truncate-1 {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 调整 Descriptions 样式 */
.custom-desc :deep(.el-descriptions__label) {
  width: 80px;
  font-weight: bold;
  background-color: #f9fafc;
}
</style>