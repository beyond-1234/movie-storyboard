<template>
  <div class="flex h-screen bg-gray-50 overflow-hidden">
    <!-- 左侧侧边栏：剧集列表 -->
    <div class="w-80 bg-white border-r border-gray-200 flex flex-col shrink-0">
      <div class="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <span class="font-bold text-gray-700 text-lg">我的剧集</span>
        <el-tooltip content="新建剧集" placement="top">
          <el-button type="primary" plain icon="Plus" circle size="small" @click="openCreateSeries" />
        </el-tooltip>
      </div>

      <div class="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar" v-loading="loadingSeries">
        <div 
          v-for="item in seriesList" 
          :key="item.id"
          class="p-4 rounded-lg cursor-pointer border transition-all duration-200 group relative"
          :class="currentSeries?.id === item.id 
            ? 'bg-blue-50 border-blue-200 shadow-sm' 
            : 'bg-white border-transparent hover:bg-gray-50 hover:border-gray-200'"
          @click="selectSeries(item)"
        >
          <div class="flex justify-between items-start mb-1">
            <span class="font-bold text-gray-800 truncate pr-6" :class="{'text-blue-700': currentSeries?.id === item.id}">
              {{ item.name }}
            </span>
            <!-- 悬浮操作按钮 -->
            <div class="hidden group-hover:flex absolute top-3 right-3 bg-white/80 rounded backdrop-blur-sm shadow-sm border border-gray-100 p-0.5">
               <el-button type="primary" link size="small" icon="Edit" @click.stop="editSeries(item)" />
               <el-button type="danger" link size="small" icon="Delete" @click.stop="deleteSeriesItem(item)" />
            </div>
          </div>
          <div class="text-xs text-gray-500 line-clamp-2 leading-relaxed h-8">
            {{ item.description || '暂无简介' }}
          </div>
          <div class="mt-2 text-[10px] text-gray-400 flex justify-between">
             <span>更新于: {{ formatDate(item.updated_time) }}</span>
          </div>
        </div>
        
        <el-empty v-if="seriesList.length === 0" description="暂无剧集，请先创建" :image-size="80" />
      </div>
    </div>

    <!-- 右侧主内容区 -->
    <div class="flex-1 flex flex-col min-w-0 bg-gray-50/50">
      <!-- 顶部工具栏 -->
      <div class="h-16 border-b border-gray-200 bg-white px-6 flex justify-between items-center shrink-0 shadow-sm z-10">
        <div class="flex items-center gap-2 text-gray-500 text-sm" v-if="currentSeries">
           <el-icon><Folder /></el-icon>
           <span>{{ currentSeries.name }}</span>
           <span class="mx-1">/</span>
           <span class="text-gray-900 font-medium">分集列表</span>
        </div>
        <div v-else></div>

        <div class="flex gap-3">
          <el-button type="info" plain icon="View" @click="openVisualAnalysis">风格分析</el-button>
          <el-button type="primary" plain icon="Plus" @click="openCreateEpisode" :disabled="!currentSeries">新建分集</el-button>
        </div>
      </div>

      <!-- 内容滚动区 -->
      <div class="flex-1 overflow-y-auto p-6 custom-scrollbar" v-loading="loadingEpisodes">
        <template v-if="currentSeries">
          <!-- 剧集信息头 -->
          <div class="mb-8 bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">{{ currentSeries.name }}</h2>
            <p class="text-gray-500 text-sm mb-4 leading-relaxed max-w-4xl">{{ currentSeries.description || '这个剧集还没有简介...' }}</p>
            
            <div class="flex gap-2 flex-wrap">
               <el-tag v-if="currentSeries.script_core_conflict" type="warning" effect="plain" size="small">
                 冲突: {{ currentSeries.script_core_conflict }}
               </el-tag>
               <el-tag v-if="currentSeries.script_emotional_keywords" type="success" effect="plain" size="small">
                 基调: {{ currentSeries.script_emotional_keywords }}
               </el-tag>
            </div>
          </div>

          <!-- 分集卡片网格 -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            <div 
              v-for="ep in episodesList" 
              :key="ep.id" 
              class="group bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300 flex flex-col h-[280px]"
            >
              <!-- 卡片头部 -->
              <div class="p-4 border-b border-gray-50 flex justify-between items-center bg-gray-50/30">
                <span class="font-bold text-gray-700 truncate flex-1 mr-2" :title="ep.film_name">{{ ep.film_name }}</span>
                <el-tag size="small" type="info" effect="dark" class="shrink-0">分集</el-tag>
              </div>
              
              <!-- 卡片内容 -->
              <div class="p-5 flex-1 overflow-hidden relative">
                <div class="text-sm text-gray-600 space-y-3">
                  <div class="flex gap-2">
                    <el-icon class="mt-0.5 text-gray-400 shrink-0"><InfoFilled /></el-icon>
                    <span class="line-clamp-3 leading-relaxed">
                      {{ ep.basic_info || '暂无基础信息，可从剧集继承...' }}
                    </span>
                  </div>
                  <div class="flex gap-2 items-center text-xs text-gray-500">
                    <el-icon class="text-gray-400"><PriceTag /></el-icon>
                    <span class="truncate">{{ ep.script_core_conflict || '无特定冲突' }}</span>
                  </div>
                </div>
                
                <!-- 遮罩层 (Hover 显示进入按钮) -->
                <div class="absolute inset-0 bg-white/90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
                  <el-button type="primary" plain round size="large" icon="EditPen" @click="enterStudio(ep)">
                    进入创作工坊
                  </el-button>
                </div>
              </div>

              <!-- 卡片底部 -->
              <div class="p-3 bg-gray-50 flex justify-end items-center gap-2 border-t border-gray-100">
                <span class="text-[10px] text-gray-400 mr-auto pl-1">ID: {{ ep.id.slice(0,6) }}</span>
                <!-- 移动端或非Hover状态下也需要能操作，保留小按钮 -->
                <el-button type="primary" link size="small" @click="enterStudio(ep)">进入</el-button>
                <el-divider direction="vertical" />
                <el-button type="danger" link size="small" @click="deleteEpisodeItem(ep)">删除</el-button>
              </div>
            </div>

            <!-- 新建分集卡片 (占位符) -->
            <div 
              class="border-2 border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center text-gray-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/20 cursor-pointer transition-all h-[280px]"
              @click="openCreateEpisode"
            >
              <el-icon size="48" class="mb-4"><Plus /></el-icon>
              <span class="font-medium">新建分集</span>
            </div>
          </div>
          
          <el-empty v-if="episodesList.length === 0" description="该剧集下暂无分集，快去创建第一个吧" class="mt-10" />
        </template>

        <el-empty v-else description="请在左侧选择一个剧集开始工作" class="mt-20">
          <template #image>
            <el-icon size="60" class="text-gray-300"><Film /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>

    <!-- 弹窗 1: 剧集编辑/新建 -->
    <el-dialog 
      v-model="seriesDialog.visible" 
      :title="seriesDialog.id ? '编辑剧集' : '新建剧集'" 
      width="600px"
      destroy-on-close
    >
      <el-form :model="seriesForm" label-width="100px" class="py-2">
        <el-form-item label="剧集名称" required>
          <el-input v-model="seriesForm.name" placeholder="例如：黑神话：悟空" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="seriesForm.description" type="textarea" :rows="2" placeholder="剧集大纲..." />
        </el-form-item>
        <el-divider content-position="left">公共设定 (所有分集默认继承)</el-divider>
        <el-form-item label="核心冲突">
          <el-input v-model="seriesForm.script_core_conflict" placeholder="全剧的核心冲突" />
        </el-form-item>
        <el-form-item label="情感关键词">
          <el-input v-model="seriesForm.script_emotional_keywords" placeholder="例如：史诗、悲壮、复仇" />
        </el-form-item>
        <el-form-item label="基础信息">
          <el-input v-model="seriesForm.basic_info" type="textarea" :rows="3" placeholder="世界观、时代背景、通用人物小传等" />
        </el-form-item>
        <el-form-item label="色彩体系">
          <el-input v-model="seriesForm.visual_color_system" type="textarea" :rows="2" placeholder="例如：黑金冷色调" />
        </el-form-item>
        <el-form-item label="视觉设定">
          <el-input v-model="seriesForm.visual_consistency_prompt" type="textarea" :rows="4" placeholder="固定角色的视觉描述 Prompt..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="seriesDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitSeries">确定</el-button>
      </template>
    </el-dialog>

    <!-- 弹窗 2: 分集新建 -->
    <el-dialog 
      v-model="episodeDialog.visible" 
      title="新建分集" 
      width="600px"
      destroy-on-close
    >
      <el-form :model="episodeForm" label-width="100px" class="py-2">
        <el-form-item label="分集名称" required>
          <el-input v-model="episodeForm.film_name" placeholder="例如：第一集：缘起" />
        </el-form-item>
        <el-alert title="以下设定默认继承自剧集，可单独修改" type="info" :closable="false" class="mb-4" />
        
        <el-form-item label="核心冲突">
          <el-input v-model="episodeForm.script_core_conflict" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="基础信息">
          <el-input v-model="episodeForm.basic_info" type="textarea" :rows="3" />
        </el-form-item>
         <el-form-item label="人物设定">
          <el-input v-model="episodeForm.visual_consistency_prompt" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="episodeDialog.visible = false">取消</el-button>
        <el-button type="primary" plain @click="submitEpisode">创建并进入</el-button>
      </template>
    </el-dialog>

    <!-- 弹窗 3: 视觉分析 -->
    <el-dialog v-model="analysisDialog.visible" title="视觉风格分析" width="500px">
      <div class="flex flex-col gap-4">
        <div 
          class="border-2 border-dashed border-gray-300 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all group"
          @click="$refs.analysisInputRef.click()"
          @drop.prevent="handleAnalysisDrop" 
          @dragover.prevent
        >
          <img v-if="analysisDialog.preview" :src="analysisDialog.preview" class="max-h-64 object-contain rounded shadow-sm" />
          <div v-else class="text-center text-gray-400 group-hover:text-blue-500 transition-colors">
            <el-icon size="48"><UploadFilled /></el-icon>
            <div class="mt-3 font-medium">点击或拖拽上传参考图</div>
            <div class="text-xs mt-1 text-gray-300">支持 JPG/PNG</div>
          </div>
          <input type="file" ref="analysisInputRef" class="hidden" accept="image/*" @change="handleAnalysisFile" />
        </div>

        <el-button type="primary" size="large" :loading="analysisDialog.analyzing" :disabled="!analysisDialog.file" @click="startVisualAnalysis">
          开始智能分析
        </el-button>

        <div v-if="analysisDialog.result" class="bg-gray-100 p-4 rounded-lg text-sm relative group border border-gray-200">
          <div class="flex justify-between items-center mb-2">
            <span class="font-bold text-gray-700 flex items-center gap-1"><el-icon><MagicStick /></el-icon> 分析结果：</span>
            <el-button type="primary" link size="small" @click="copyAnalysisResult">复制</el-button>
          </div>
          <div class="whitespace-pre-wrap text-gray-600 leading-relaxed max-h-60 overflow-y-auto custom-scrollbar">{{ analysisDialog.result }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { 
  getSeriesList, createSeries, updateSeries, deleteSeries, getSeriesEpisodes, 
  createProject, deleteProject 
} from '@/api/project'
import { analyzeImage } from '@/api/generation'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// --- State: Series ---
const seriesList = ref([])
const currentSeries = ref(null)
const loadingSeries = ref(false)
const seriesDialog = ref({ visible: false, id: null }) // id存在即编辑
const seriesForm = ref({})

// --- State: Episodes ---
const episodesList = ref([])
const loadingEpisodes = ref(false)
const episodeDialog = ref({ visible: false })
const episodeForm = ref({})

// --- State: Analysis ---
const analysisDialog = ref({ visible: false, file: null, preview: '', result: '', analyzing: false })
const analysisInputRef = ref(null)

// --- Initialization ---

onMounted(async () => {
  await fetchSeries()
})

const fetchSeries = async () => {
  loadingSeries.value = true
  try {
    const res = await getSeriesList()
    seriesList.value = res || []
    if (seriesList.value.length > 0 && !currentSeries.value) {
      selectSeries(seriesList.value[0])
    }
  } catch (e) {
    console.error(e)
  } finally {
    loadingSeries.value = false
  }
}

const selectSeries = async (item) => {
  currentSeries.value = item
  await fetchEpisodes(item.id)
}

// --- Methods: Series ---

const openCreateSeries = () => {
  seriesForm.value = {
    name: '', description: '',
    script_core_conflict: '', script_emotional_keywords: '',
    basic_info: '', visual_color_system: '', visual_consistency_prompt: ''
  }
  seriesDialog.value = { visible: true, id: null }
}

const editSeries = (item) => {
  seriesForm.value = JSON.parse(JSON.stringify(item))
  seriesDialog.value = { visible: true, id: item.id }
}

const submitSeries = async () => {
  if (!seriesForm.value.name) return ElMessage.warning('名称必填')
  
  try {
    let res
    if (seriesDialog.value.id) {
      res = await updateSeries(seriesDialog.value.id, seriesForm.value)
      // 更新列表
      const idx = seriesList.value.findIndex(s => s.id === res.id)
      if (idx !== -1) seriesList.value[idx] = res
      if (currentSeries.value?.id === res.id) currentSeries.value = res
      ElMessage.success('更新成功')
    } else {
      res = await createSeries(seriesForm.value)
      seriesList.value.unshift(res)
      selectSeries(res)
      ElMessage.success('创建成功')
    }
    seriesDialog.value.visible = false
  } catch (e) {
    console.error(e)
  }
}

const deleteSeriesItem = async (item) => {
  try {
    await ElMessageBox.confirm(`确定删除剧集 "${item.name}" 及其所有分集吗?`, '警告', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteSeries(item.id)
    seriesList.value = seriesList.value.filter(s => s.id !== item.id)
    if (currentSeries.value?.id === item.id) {
      currentSeries.value = null
      episodesList.value = []
      if (seriesList.value.length > 0) selectSeries(seriesList.value[0])
    }
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

// --- Methods: Episodes ---

const fetchEpisodes = async (sid) => {
  loadingEpisodes.value = true
  try {
    const res = await getSeriesEpisodes(sid)
    episodesList.value = res || []
  } catch (e) {
    console.error(e)
  } finally {
    loadingEpisodes.value = false
  }
}

const openCreateEpisode = () => {
  if (!currentSeries.value) return
  const s = currentSeries.value
  
  episodeForm.value = {
    film_name: '',
    // 继承剧集属性
    script_core_conflict: s.script_core_conflict || '',
    script_emotional_keywords: s.script_emotional_keywords || '',
    basic_info: s.basic_info || '',
    visual_color_system: s.visual_color_system || '',
    visual_consistency_prompt: s.visual_consistency_prompt || '',
    series_id: s.id
  }
  episodeDialog.value.visible = true
}

const submitEpisode = async () => {
  if (!episodeForm.value.film_name) return ElMessage.warning('分集名称必填')
  
  try {
    // 调用 createProject 接口 (分集即项目)
    const res = await createProject(episodeForm.value)
    episodeDialog.value.visible = false
    enterStudio(res)
    ElMessage.success('创建成功')
  } catch (e) {
    console.error(e)
  }
}

const deleteEpisodeItem = async (ep) => {
  try {
    await ElMessageBox.confirm(`确定删除分集 "${ep.film_name}" 吗?`, '警告', { type: 'warning' })
    await deleteProject(ep.id)
    episodesList.value = episodesList.value.filter(e => e.id !== ep.id)
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

const enterStudio = (ep) => {
  router.push({ 
    name: 'ProjectSpace', 
    params: { id: ep.id },
    query: { series_id: ep.series_id } 
  })
}

// --- Methods: Visual Analysis ---

const openVisualAnalysis = () => {
  analysisDialog.value = { visible: true, file: null, preview: '', result: '', analyzing: false }
}

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
  analysisDialog.value.file = file
  analysisDialog.value.preview = URL.createObjectURL(file)
  analysisDialog.value.result = ''
}

const startVisualAnalysis = async () => {
  analysisDialog.value.analyzing = true
  try {
    const res = await analyzeImage(analysisDialog.value.file)
    if (res.success) {
      analysisDialog.value.result = res.style_description
      ElMessage.success('分析完成')
    } else {
      ElMessage.error(res.error || '分析失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('请求失败')
  } finally {
    analysisDialog.value.analyzing = false
  }
}

const copyAnalysisResult = () => {
  if (!analysisDialog.value.result) return
  navigator.clipboard.writeText(analysisDialog.value.result)
  ElMessage.success('已复制')
}

const formatDate = (str) => {
  if (!str) return '-'
  return new Date(str).toLocaleDateString()
}
</script>

<style scoped>
/* 自定义滚动条 */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 3px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #d1d5db;
}
</style>