<template>
  <div class="series-page">
    <!-- 左侧侧边栏：剧集列表 -->
    <div class="series-sidebar">
      <div class="sidebar-header">
        <span class="title">我的剧集</span>
        <el-tooltip content="新建剧集" placement="top">
          <el-button type="primary" :icon="Plus" circle size="small" @click="openCreateSeries" />
        </el-tooltip>
      </div>

      <div class="sidebar-list custom-scrollbar" v-loading="loadingSeries">
        <div 
          v-for="item in seriesList" 
          :key="item.id"
          class="series-item"
          :class="{ 'active': currentSeries?.id === item.id }"
          @click="selectSeries(item)"
        >
          <div class="item-header">
            <span class="item-name" :title="item.name">{{ item.name }}</span>
            <!-- 悬浮操作按钮 -->
            <div class="item-actions">
               <el-button type="primary" link size="small" :icon="Edit" @click.stop="editSeries(item)" />
               <el-button type="danger" link size="small" :icon="Delete" @click.stop="deleteSeriesItem(item)" />
            </div>
          </div>
          <div class="item-desc" :title="item.description">
            {{ item.description || '暂无简介' }}
          </div>
          <div class="item-meta">
             <span>更新于: {{ formatDate(item.updated_time) }}</span>
          </div>
        </div>
        
        <el-empty v-if="seriesList.length === 0" description="暂无剧集，请先创建" :image-size="80" />
      </div>
    </div>

    <!-- 右侧主内容区 -->
    <div class="series-main">
      <!-- 顶部工具栏 -->
      <div class="main-header">
        <div class="breadcrumb" v-if="currentSeries">
           <el-icon><Folder /></el-icon>
           <span>{{ currentSeries.name }}</span>
           <span class="separator">/</span>
           <span class="current">分集列表</span>
        </div>
        <div v-else></div>

        <div class="header-actions">
          <el-button type="info" plain :icon="View" @click="openVisualAnalysis">风格分析</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreateEpisode" :disabled="!currentSeries">新建分集</el-button>
        </div>
      </div>

      <!-- 内容滚动区 -->
      <div class="main-content custom-scrollbar" v-loading="loadingEpisodes">
        <template v-if="currentSeries">
          <!-- 剧集信息头 -->
          <div class="series-info-card">
            <h2 class="info-title">{{ currentSeries.name }}</h2>
            <p class="info-desc">{{ currentSeries.description || '这个剧集还没有简介...' }}</p>
            
            <div class="info-tags">
               <el-tag v-if="currentSeries.script_core_conflict" type="warning" effect="plain" size="small"
                  style="white-space: pre-wrap; height: auto; text-align: left; padding: 4px 8px;">
                 冲突: {{ currentSeries.script_core_conflict }}
               </el-tag>
               <el-tag v-if="currentSeries.script_emotional_keywords" type="success" effect="plain" size="small"
                  style="white-space: pre-wrap; height: auto; text-align: left; padding: 4px 8px;">
                 基调: {{ currentSeries.script_emotional_keywords }}
               </el-tag>
            </div>
          </div>

          <!-- 分集卡片网格 -->
          <div class="episode-grid">
            <div 
              v-for="ep in episodesList" 
              :key="ep.id" 
              class="episode-card"
            >
              <!-- 卡片头部 -->
              <div class="card-header">
                <span class="card-title" :title="ep.film_name">{{ ep.film_name }}</span>
                <el-tag size="small" type="info" effect="dark">分集</el-tag>
              </div>
              
              <!-- 卡片内容 -->
              <div class="card-body">
                <div class="card-info">
                  <div class="info-row">
                    <el-icon><InfoFilled /></el-icon>
                    <span class="text">
                      {{ ep.basic_info ? (ep.basic_info.length > 50 ? ep.basic_info.slice(0,50)+'...' : ep.basic_info) : '暂无基础信息...' }}
                    </span>
                  </div>
                  <div class="info-row conflict">
                    <el-icon><PriceTag /></el-icon>
                    <span style="white-space: pre-wrap; line-height: 1.4;">{{ ep.script_core_conflict || '无特定冲突' }}</span>
                  </div>
                </div>
                
                <!-- 遮罩层 -->
                <div class="card-mask">
                  <el-button type="primary" round :icon="EditPen" @click="enterStudio(ep)">
                    进入创作工坊
                  </el-button>
                </div>
              </div>

              <!-- 卡片底部 -->
              <div class="card-footer">
                <span class="ep-id">ID: {{ ep.id.slice(0,6) }}</span>
                <div class="footer-btns">
                  <el-button type="primary" link size="small" @click="enterStudio(ep)">进入</el-button>
                  <el-divider direction="vertical" />
                  <el-button type="danger" link size="small" @click="deleteEpisodeItem(ep)">删除</el-button>
                </div>
              </div>
            </div>

            <!-- 新建分集卡片 -->
            <div class="create-card" @click="openCreateEpisode">
              <el-icon class="create-icon"><Plus /></el-icon>
              <span class="create-text">新建分集</span>
            </div>
          </div>
          
          <el-empty v-if="episodesList.length === 0" description="该剧集下暂无分集，快去创建第一个吧" class="empty-state" />
        </template>

        <el-empty v-else description="请在左侧选择一个剧集开始工作" class="empty-select">
          <template #image>
            <el-icon size="60" color="#e0e0e0"><Film /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>

    <!-- 弹窗 1: 剧集编辑/新建 -->
    <el-dialog 
      v-model="seriesDialog.visible" 
      :title="seriesDialog.id ? '编辑剧集' : '新建剧集'" 
      width="1600px"
      destroy-on-close
    >
      <!-- AI 智能辅助模块 -->
      <div class="bg-blue-50 p-3 rounded mb-4 border border-blue-100">
        <div class="flex items-center justify-between mb-2">
           <span class="text-sm font-bold text-blue-700 flex items-center gap-1">
             <el-icon><MagicStick /></el-icon> AI 智能辅助 (输入剧本片段)
           </span>
           <ModelSelector 
             type="text" 
             label="文本模型" 
             v-model:provider="aiConfig.providerId" 
             v-model:model="aiConfig.modelName" 
           />
        </div>
        <el-input 
          v-model="aiScriptContent" 
          type="textarea" 
          :rows="6" 
          placeholder="在此粘贴小说或剧本片段，AI 将自动分析并填充下方字段..." 
          class="mb-2"
        />
        <div class="text-right">
          <el-button 
            type="primary" 
            size="small" 
            :loading="aiGenerating" 
            :disabled="!aiScriptContent" 
            @click="handleAiGenerate"
          >
            一键生成设定
          </el-button>
        </div>
      </div>

      <el-form :model="seriesForm" label-width="100px" class="py-2">
        <el-form-item label="剧集名称" required>
          <el-input v-model="seriesForm.name" placeholder="例如：黑神话：悟空" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="seriesForm.description" type="textarea" :rows="6" placeholder="剧集大纲..." />
        </el-form-item>
        
        <el-divider content-position="left">公共设定 (所有分集默认继承)</el-divider>
        
        <el-form-item label="核心冲突">
          <el-input v-model="seriesForm.script_core_conflict" type="textarea" :rows="6" placeholder="全剧的核心冲突 (支持换行)" />
        </el-form-item>
        <el-form-item label="情感关键词">
          <el-input v-model="seriesForm.script_emotional_keywords" placeholder="例如：史诗、悲壮、复仇" />
        </el-form-item>
        <el-form-item label="基础信息">
          <el-input v-model="seriesForm.basic_info" type="textarea" :rows="6" placeholder="世界观、时代背景、通用人物小传等" />
        </el-form-item>
        <el-form-item label="色彩体系">
          <el-input v-model="seriesForm.visual_color_system" type="textarea" :rows="6" placeholder="例如：黑金冷色调" />
        </el-form-item>
        <el-form-item label="视觉设定">
          <el-input v-model="seriesForm.visual_consistency_prompt" type="textarea" :rows="6" placeholder="固定角色的视觉描述 Prompt..." />
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
      width="1600px"
      destroy-on-close
    >
      <el-form :model="episodeForm" label-width="100px" class="py-2">
        <el-form-item label="分集名称" required>
          <el-input v-model="episodeForm.film_name" placeholder="例如：第一集：缘起" />
        </el-form-item>
        <el-alert title="以下设定默认继承自剧集，可单独修改" type="info" :closable="false" class="mb-4" />
        
        <el-form-item label="核心冲突">
          <el-input v-model="episodeForm.script_core_conflict" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="基础信息">
          <el-input v-model="episodeForm.basic_info" type="textarea" :rows="6" />
        </el-form-item>
         <el-form-item label="人物设定">
          <el-input v-model="episodeForm.visual_consistency_prompt" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="episodeDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitEpisode">创建并进入</el-button>
      </template>
    </el-dialog>

    <!-- 弹窗 3: 视觉分析 -->
    <el-dialog v-model="analysisDialog.visible" title="视觉风格分析" width="500px">
      <div class="analysis-container">
        <div 
          class="upload-area"
          @click="$refs.analysisInputRef.click()"
          @drop.prevent="handleAnalysisDrop" 
          @dragover.prevent
        >
          <img v-if="analysisDialog.preview" :src="analysisDialog.preview" class="preview-img" />
          <div v-else class="upload-placeholder">
            <el-icon size="48"><UploadFilled /></el-icon>
            <div class="text">点击或拖拽上传参考图</div>
            <div class="sub-text">支持 JPG/PNG</div>
          </div>
          <input type="file" ref="analysisInputRef" class="hidden-input" accept="image/*" @change="handleAnalysisFile" />
        </div>

        <el-button type="primary" size="large" :loading="analysisDialog.analyzing" :disabled="!analysisDialog.file" @click="startVisualAnalysis" class="analyze-btn">
          开始智能分析
        </el-button>

        <div v-if="analysisDialog.result" class="result-box">
          <div class="result-header">
            <span class="label"><el-icon><MagicStick /></el-icon> 分析结果：</span>
            <el-button type="primary" link size="small" @click="copyAnalysisResult">复制</el-button>
          </div>
          <div class="result-content custom-scrollbar">{{ analysisDialog.result }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  getSeriesList, createSeries, updateSeries, deleteSeries, getSeriesEpisodes, 
  createProject, deleteProject 
} from '@/api/project'
import { analyzeImage, analyzeSeriesScript } from '@/api/generation' // 引入新API
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Edit, Delete, Folder, View, EditPen, InfoFilled, 
  PriceTag, Film, UploadFilled, MagicStick 
} from '@element-plus/icons-vue'
import ModelSelector from '@/components/ModelSelector.vue' // 引入 ModelSelector

const router = useRouter()

// --- State ---
const seriesList = ref([])
const currentSeries = ref(null)
const loadingSeries = ref(false)
const episodesList = ref([])
const loadingEpisodes = ref(false)

const seriesDialog = ref({ visible: false, id: null })
const seriesForm = ref({})
const episodeDialog = ref({ visible: false })
const episodeForm = ref({})
const analysisDialog = ref({ visible: false, file: null, preview: '', result: '', analyzing: false })
const analysisInputRef = ref(null)

// AI 辅助相关状态
const aiScriptContent = ref('')
const aiConfig = ref({ providerId: '', modelName: '' })
const aiGenerating = ref(false)

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

// --- AI Generate Series Fields ---

const handleAiGenerate = async () => {
  if (!aiScriptContent.value) return ElMessage.warning('请先输入剧本内容')
  if (!aiConfig.value.providerId) return ElMessage.warning('请选择 AI 模型')

  aiGenerating.value = true
  try {
    const res = await analyzeSeriesScript({
      content: aiScriptContent.value,
      provider_id: aiConfig.value.providerId,
      model_name: aiConfig.value.modelName
    })
    
    if (res) {
      // 智能回填：如果 API 返回了字段，则覆盖表单
      if (res.name) seriesForm.value.name = res.name
      if (res.description) seriesForm.value.description = res.description
      if (res.script_core_conflict) seriesForm.value.script_core_conflict = res.script_core_conflict
      if (res.script_emotional_keywords) seriesForm.value.script_emotional_keywords = res.script_emotional_keywords
      if (res.basic_info) seriesForm.value.basic_info = res.basic_info
      if (res.visual_color_system) seriesForm.value.visual_color_system = res.visual_color_system
      if (res.visual_consistency_prompt) seriesForm.value.visual_consistency_prompt = res.visual_consistency_prompt
      
      ElMessage.success('分析完成，表单已自动填充')
    }
  } catch (e) {
    console.error(e)
  } finally {
    aiGenerating.value = false
  }
}

// --- Series CRUD ---
const openCreateSeries = () => {
  // 重置表单和 AI 状态
  seriesForm.value = {
    name: '', description: '',
    script_core_conflict: '', script_emotional_keywords: '',
    basic_info: '', visual_color_system: '', visual_consistency_prompt: ''
  }
  aiScriptContent.value = ''
  seriesDialog.value = { visible: true, id: null }
}

const editSeries = (item) => {
  seriesForm.value = JSON.parse(JSON.stringify(item))
  aiScriptContent.value = ''
  seriesDialog.value = { visible: true, id: item.id }
}

const submitSeries = async () => {
  if (!seriesForm.value.name) return ElMessage.warning('名称必填')
  try {
    let res
    if (seriesDialog.value.id) {
      res = await updateSeries(seriesDialog.value.id, seriesForm.value)
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
  } catch (e) { console.error(e) }
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
  } catch (e) { if (e !== 'cancel') console.error(e) }
}

// --- Episode CRUD ---
const openCreateEpisode = () => {
  if (!currentSeries.value) return
  const s = currentSeries.value
  episodeForm.value = {
    film_name: '',
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
    const res = await createProject(episodeForm.value)
    episodeDialog.value.visible = false
    enterStudio(res)
    ElMessage.success('创建成功')
  } catch (e) { console.error(e) }
}

const deleteEpisodeItem = async (ep) => {
  try {
    await ElMessageBox.confirm(`确定删除分集 "${ep.film_name}" 吗?`, '警告', { type: 'warning' })
    await deleteProject(ep.id)
    episodesList.value = episodesList.value.filter(e => e.id !== ep.id)
    ElMessage.success('删除成功')
  } catch (e) { if (e !== 'cancel') console.error(e) }
}

const enterStudio = (ep) => {
  router.push({ 
    name: 'ProjectSpace', 
    params: { id: ep.id },
    query: { series_id: ep.series_id } 
  })
}

// --- Analysis ---
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
  } catch (e) { console.error(e) } finally { analysisDialog.value.analyzing = false }
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
/* 核心布局 - Flexbox 兜底 */
.series-page {
  display: flex;
  height: 100vh;
  background-color: #f9fafb; /* gray-50 */
  overflow: hidden;
}

/* 侧边栏样式 */
.series-sidebar {
  width: 320px;
  background-color: #fff;
  border-right: 1px solid #e5e7eb; /* gray-200 */
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #f3f4f6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: rgba(249, 250, 251, 0.5);
}

.title {
  font-weight: bold;
  color: #374151;
  font-size: 18px;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.series-item {
  padding: 16px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
  margin-bottom: 8px;
  position: relative;
  background: #fff;
}

.series-item:hover {
  background-color: #f9fafb;
  border-color: #e5e7eb;
}

.series-item.active {
  background-color: #eff6ff; /* blue-50 */
  border-color: #bfdbfe; /* blue-200 */
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 4px;
}

.item-name {
  font-weight: bold;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 12px;
  flex: 1;
}

.active .item-name {
  color: #1d4ed8; /* blue-700 */
}

.item-actions {
  display: none;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px;
  border-radius: 4px;
}

.series-item:hover .item-actions {
  display: flex;
}

.item-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 36px;
}

.item-meta {
  margin-top: 8px;
  font-size: 10px;
  color: #9ca3af;
}

/* 主内容区样式 */
.series-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background-color: rgba(249, 250, 251, 0.5);
}

.main-header {
  height: 64px;
  border-bottom: 1px solid #e5e7eb;
  background-color: #fff;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #6b7280;
}

.current {
  color: #111827;
  font-weight: 500;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.series-info-card {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  border: 1px solid #f3f4f6;
  margin-bottom: 32px;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.info-title {
  font-size: 24px;
  font-weight: bold;
  color: #1f2937;
  margin-bottom: 8px;
}

.info-desc {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 16px;
  line-height: 1.6;
}

.info-tags {
  display: flex;
  gap: 8px;
}

/* 卡片网格布局 - 纯 CSS 实现 */
.episode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.episode-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 280px;
  transition: all 0.3s;
  position: relative;
}

.episode-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.card-header {
  padding: 16px;
  border-bottom: 1px solid #f9fafb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: rgba(249, 250, 251, 0.3);
}

.card-title {
  font-weight: bold;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  margin-right: 8px;
}

.card-body {
  padding: 20px;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.card-info {
  font-size: 14px;
  color: #4b5563;
}

.info-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.info-row .text {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.info-row.conflict {
  align-items: center;
  font-size: 12px;
  color: #6b7280;
}

/* 遮罩层 */
.card-mask {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.episode-card:hover .card-mask {
  opacity: 1;
}

.card-footer {
  padding: 12px;
  background-color: #f9fafb;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  border-top: 1px solid #f3f4f6;
  gap: 8px;
}

.ep-id {
  font-size: 10px;
  color: #9ca3af;
  margin-right: auto;
  padding-left: 4px;
}

/* 新建卡片 */
.create-card {
  border: 2px dashed #e5e7eb;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.3s;
  height: 280px;
}

.create-card:hover {
  border-color: #60a5fa;
  color: #3b82f6;
  background-color: rgba(239, 246, 255, 0.2);
}

.create-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* 分析弹窗样式 */
.analysis-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.preview-img {
  max-height: 256px;
  object-fit: contain;
  border-radius: 4px;
}

.upload-placeholder {
  text-align: center;
  color: #9ca3af;
}

.analyze-btn {
  width: 100%;
}

.result-box {
  background: #f3f4f6;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-content {
  white-space: pre-wrap;
  color: #4b5563;
  line-height: 1.6;
  max-height: 240px;
  overflow-y: auto;
  font-size: 14px;
}

/* 滚动条美化 */
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

/* 隐藏 Input */
.hidden-input {
  display: none;
}
</style>