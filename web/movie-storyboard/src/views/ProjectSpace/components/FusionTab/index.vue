<template>
  <div class="fusion-tab h-full flex flex-col bg-gray-50">
    <!-- 顶部配置栏 -->
    <div class="bg-white px-6 py-3 border-b border-gray-200 flex justify-between items-center shadow-sm z-10 shrink-0">
      <div class="flex flex-wrap gap-4 items-center">
        <ModelSelector type="text" label="文本模型" v-model:provider="store.genOptions.textProviderId" v-model:model="store.genOptions.textModelName" />
        <div class="w-px h-6 bg-gray-200 hidden md:block"></div>
        <ModelSelector type="image_fusion" label="图生图模型" v-model:provider="store.genOptions.fusionProviderId" v-model:model="store.genOptions.fusionModelName" />
        <div class="w-px h-6 bg-gray-200 hidden md:block"></div>
        <ModelSelector type="video" label="视频模型" v-model:provider="store.genOptions.videoProviderId" v-model:model="store.genOptions.videoModelName" />
      </div>

      <div class="flex gap-2">
        <el-dropdown split-button type="success" size="small" @click="openBatchDialog('image')" @command="openBatchDialog">
          批量生成
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="prompt">批量生成提示词</el-dropdown-item>
              <el-dropdown-item command="image">批量生成首帧</el-dropdown-item>
              <el-dropdown-item command="end_image">批量生成尾帧</el-dropdown-item>
              <el-dropdown-item command="video" divided>批量生成视频</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        
        <el-button type="danger" plain size="small" :icon="Delete" :disabled="selectedIds.length === 0" @click="handleBatchDelete">批量删除</el-button>
        <el-button type="warning" plain size="small" :icon="CopyDocument" @click="handleCopyFromScenes">从场景复制</el-button>
        <el-button type="primary" size="small" :icon="Plus" @click="openCreateDialog">添加任务</el-button>
      </div>
    </div>

    <!-- 自定义表头 -->
    <div class="grid grid-cols-[60px_1fr_640px] gap-4 px-6 py-2 bg-gray-100/80 text-xs font-medium text-gray-500 border-b border-gray-200 shrink-0 select-none">
      <div class="text-center pl-4">场次</div>
      <div class="pl-2">任务详情 (描述、提示词、素材)</div>
      <div class="text-left pl-2">生成结果 (首帧/尾帧/视频)</div>
    </div>

    <!-- 融图任务列表 (卡片式) -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
      <div 
        v-for="(item, index) in store.fusionList" 
        :key="item.id" 
        class="fusion-card group relative transition-all duration-200"
        :class="{ 'ring-2 ring-blue-400 bg-blue-50/30': selectedIds.includes(item.id) }"
        @click="toggleSelection(item.id)"
      >
        <!-- 1. 索引区块 -->
        <div class="index-section" @click.stop>
          <div class="mb-2" @click.stop>
             <el-checkbox 
               :model-value="selectedIds.includes(item.id)" 
               @change="toggleSelection(item.id)" 
             />
          </div>
          <div class="scene-badge">
            <span class="label">场</span>
            <span class="value">{{ item.scene }}</span>
          </div>
          <div class="divider-vertical"></div>
          <div class="shot-badge">
            <span class="label">镜</span>
            <span class="value">{{ item.shot_number }}</span>
          </div>
        </div>

        <!-- 2. 内容详情区块 -->
        <div class="content-section">
          <!-- 文本信息区 -->
          <div class="text-info-area space-y-2 mb-3">
            <!-- 场景说明 -->
            <div v-if="item.scene_description" class="flex items-start gap-2 text-xs text-gray-500">
              <el-icon class="mt-0.5 shrink-0"><Collection /></el-icon>
              <span>{{ item.scene_description }}</span>
            </div>

            <!-- 画面描述 -->
            <div class="flex items-start gap-2">
              <el-icon class="mt-1 text-gray-700 text-xs shrink-0"><Document /></el-icon>
              <span class="text-sm text-gray-800 font-medium leading-snug">{{ item.visual_description || '暂无画面描述' }}</span>
            </div>

            <!-- 对白与声音 -->
            <div v-if="item.dialogue || item.audio_description" class="flex items-start gap-2 bg-blue-50/50 p-2 rounded border border-blue-100/50">
              <el-icon class="mt-1 text-blue-500 text-xs shrink-0"><Microphone /></el-icon>
              <div class="flex flex-col gap-1">
                <span v-if="item.dialogue" class="text-xs text-blue-700 font-medium">“{{ item.dialogue }}”</span>
                <span v-if="item.audio_description" class="text-[10px] text-gray-500 italic">({{ item.audio_description }})</span>
              </div>
            </div>

            <!-- 提示词展示区 (修改：支持换行显示) -->
            <div class="prompts-area space-y-1 mt-2">
              <!-- 首帧提示词 -->
              <div v-if="item.fusion_prompt" class="text-[11px] text-gray-600 bg-gray-100 p-2 rounded border border-gray-200 font-mono break-all whitespace-pre-wrap relative group/prompt leading-relaxed">
                <span class="text-blue-600 font-bold mr-1 select-none block mb-1">首帧 Prompt:</span>
                <span class="block">{{ item.fusion_prompt }}</span>
              </div>
              
              <!-- 尾帧提示词 -->
              <div v-if="item.end_frame_prompt" class="text-[11px] text-gray-600 bg-gray-100 p-2 rounded border border-gray-200 font-mono break-all whitespace-pre-wrap relative group/prompt leading-relaxed">
                <span class="text-purple-600 font-bold mr-1 select-none block mb-1">尾帧 Prompt:</span>
                <span class="block">{{ item.end_frame_prompt }}</span>
              </div>
            </div>
          </div>

          <!-- 素材区域 (底图 + 元素) -->
          <div class="flex flex-wrap gap-2 items-end">
            <!-- 底图 -->
            <div class="relative group/asset">
              <UnifiedImageCard
                :src="item.base_image"
                width="200px"
                height="200px"
                fit="cover"
                placeholder="底图"
                :enable-generate="false"
                :show-empty-actions="false"
                :enable-delete="!!item.base_image"
                custom-class="border-dashed"
                @upload="(file) => handleBaseUpload(item, file)"
                @delete="handleDeleteBaseImage(item)"
                @click-empty="triggerBaseUpload(item)"
              />
              <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400 scale-90">底图</span>
            </div>

            <!-- 加号 -->
            <div class="text-gray-300 pb-4">
              <el-icon><Plus /></el-icon>
            </div>

            <!-- 元素列表 -->
            <div 
              v-for="el in item.elements" 
              :key="el.id" 
              class="relative group/asset"
            >
              <UnifiedImageCard
                :src="el.image_url"
                width="200px"
                height="200px"
                fit="cover"
                placeholder="元素"
                :enable-generate="false"
                :enable-upload="false"
                :enable-delete="true"
                @delete="removeElement(item, el)"
              />
              <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400 truncate scale-90">{{ el.name }}</span>
            </div>

            <!-- 添加元素按钮 -->
            <el-button 
              circle 
              size="small" 
              class="mb-3 ml-1 !w-8 !h-8" 
              :icon="Plus" 
              @click.stop="openElementDialog(item)" 
            />
          </div>
        </div>

        <!-- 3. 生成结果区块 (宽度加宽，图片尺寸增大) -->
        <div class="result-section">
          <div class="grid grid-cols-3 gap-4 w-full h-full items-center justify-items-center">
            
            <!-- 首帧 -->
            <div class="result-item w-[200px]">
              <UnifiedImageCard
                :src="item.result_image"
                width="200px"
                height="200px"
                fit="cover"
                placeholder="首帧"
                :enable-delete="!!item.result_image"
                :enable-upload="true"
                @generate="generateImage(item)"
                @upload="(file) => handleResultUpload(item, file)"
                @delete="handleDeleteResultImage(item)"
              >
                <template #info>Start Frame</template>
              </UnifiedImageCard>
            </div>

            <!-- 尾帧 -->
            <div class="result-item w-[200px]">
              <UnifiedImageCard
                :src="item.end_frame_image"
                width="200px"
                height="200px"
                fit="cover"
                placeholder="尾帧"
                :enable-delete="!!item.end_frame_image"
                :enable-upload="true"
                @generate="generateEndImage(item)"
                @upload="(file) => handleEndFrameUpload(item, file)"
                @delete="handleDeleteEndFrameImage(item)"
              >
                <template #info>End Frame</template>
              </UnifiedImageCard>
            </div>

            <!-- 视频 -->
            <div class="result-item w-[200px] relative group/video">
              <div 
                v-if="item.video_url" 
                class="w-[200px] h-[200px] bg-black rounded border border-gray-800 overflow-hidden cursor-pointer relative shadow-sm"
                @click.stop="playVideo(item.video_url)"
              >
                <video :src="item.video_url" class="w-full h-full object-cover opacity-80 group-hover/video:opacity-100 transition-opacity"></video>
                <div class="absolute inset-0 flex items-center justify-center">
                  <el-icon class="text-white text-4xl drop-shadow-md opacity-80 group-hover/video:opacity-100 transition-opacity"><VideoPlay /></el-icon>
                </div>
                <!-- 视频删除按钮 -->
                <div class="absolute top-2 right-2 hidden group-hover/video:block" @click.stop="handleDeleteVideo(item)">
                   <el-button type="danger" circle size="small" :icon="Delete" />
                </div>
              </div>
              <div 
                v-else 
                class="w-[200px] h-[200px] bg-gray-50 border border-dashed rounded flex flex-col items-center justify-center text-gray-300 cursor-pointer hover:bg-gray-100 hover:text-blue-400 transition-colors"
                @click.stop="generateVideo(item)"
              >
                <el-icon :size="32"><VideoCamera /></el-icon>
                <span class="text-xs mt-2 font-medium">生成视频</span>
              </div>
            </div>

          </div>
        </div>

        <!-- 悬浮操作栏 -->
        <div class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 bg-white/90 p-1 rounded shadow-sm border border-gray-100 backdrop-blur-sm z-10" @click.stop>
           <el-tooltip content="编辑" placement="top">
             <el-button type="primary" circle size="small" :icon="Edit" @click.stop="openEditDialog(item)" />
           </el-tooltip>
           <el-tooltip content="生成提示词" placement="top">
             <el-button type="warning" circle size="small" :icon="MagicStick" @click.stop="generatePrompt(item)" />
           </el-tooltip>
           <el-tooltip content="生成首帧" placement="top">
             <el-button type="success" circle size="small" :icon="Picture" @click.stop="generateImage(item)" />
           </el-tooltip>
           <el-tooltip content="生成尾帧" placement="top">
             <el-button type="success" plain circle size="small" :icon="PictureFilled" @click.stop="generateEndImage(item)" />
           </el-tooltip>
           <el-tooltip content="生成视频" placement="top">
             <el-button type="primary" plain circle size="small" :icon="VideoCamera" :disabled="!item.result_image" @click.stop="generateVideo(item)" />
           </el-tooltip>
           <el-tooltip content="向下插入" placement="top">
             <el-button type="info" circle size="small" :icon="Plus" @click.stop="insertFusion(index)" />
           </el-tooltip>
           <el-tooltip content="删除" placement="top">
             <el-button type="danger" circle size="small" :icon="Delete" @click.stop="handleDelete(item)" />
           </el-tooltip>
        </div>
      </div>

      <el-empty v-if="store.fusionList.length === 0" description="暂无融图任务，请从场景复制或添加" />
    </div>

    <!-- 弹窗组件 -->
    <FusionEditDialog v-model="editDialogVisible" :initial-data="currentEditingRow" @success="refreshList" />
    <ElementDialog v-model="elementDialogVisible" :fusion="currentElementFusion" @success="handleElementSuccess" />
    <BatchDialog v-model="batchDialogVisible" :type="batchType" :selection="getSelectedItems()" @confirm="handleBatchConfirm" />
    
    <!-- 视频预览 -->
    <el-dialog v-model="videoPreviewVisible" title="视频预览" width="60%" destroy-on-close align-center>
      <video v-if="currentVideoUrl" :src="currentVideoUrl" controls autoplay class="w-full max-h-[70vh]"></video>
    </el-dialog>

    <!-- 隐藏的上传 input (用于 UnifiedImageCard click-empty 的 fallback) -->
    <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="handleFileSelected" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import ModelSelector from '@/components/ModelSelector.vue'
import FusionEditDialog from './FusionEditDialog.vue'
import ElementDialog from './ElementDialog.vue'
import BatchDialog from './BatchDialog.vue'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'

import { 
  getFusions, deleteFusion, createFusion, updateFusion, batchDeleteShots // 注意：融图批量删除如果还没API，暂时循环删
} from '@/api/project' 
import { 
  generateFusionPrompt as apiGenPrompt, 
  generateFusionImage as apiGenImage, 
  generateFusionVideo as apiGenVideo,
  uploadBaseImage
} from '@/api/generation'

import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { 
  Delete, CopyDocument, Plus, VideoPlay, VideoCamera, 
  Document, Microphone, Edit, MagicStick, Picture, PictureFilled, Collection
} from '@element-plus/icons-vue'

const store = useProjectStore()
const loadingStore = useLoadingStore()

// State
const selectedIds = ref([])
const editDialogVisible = ref(false)
const elementDialogVisible = ref(false)
const batchDialogVisible = ref(false)
const videoPreviewVisible = ref(false)
const currentVideoUrl = ref('')
const currentEditingRow = ref(null)
const currentElementFusion = ref(null)
const batchType = ref('image')

const fileInput = ref(null)
const uploadTargetRow = ref(null)

// Initialization
onMounted(() => {
  refreshList()
})

const refreshList = async () => {
  if (!store.currentProjectId) return
  if (store.loading) store.loading.fusions = true
  try {
    const res = await getFusions(store.currentProjectId)
    store.fusionList = res || []
    selectedIds.value = []
  } finally {
    if (store.loading) store.loading.fusions = false
  }
}

// Helpers
const getSelectedItems = () => {
  return store.fusionList.filter(item => selectedIds.value.includes(item.id))
}

// Selection
const toggleSelection = (id) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx > -1) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

// Actions
const openCreateDialog = () => {
  currentEditingRow.value = null
  editDialogVisible.value = true
}

const openEditDialog = (row) => {
  currentEditingRow.value = row
  editDialogVisible.value = true
}

const insertFusion = (index) => {
  currentEditingRow.value = { insertIndex: index + 1 }
  editDialogVisible.value = true
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm('确定删除该任务?')
  await deleteFusion(store.currentProjectId, row.id)
  refreshList()
}

const handleBatchDelete = async () => {
  await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个任务?`)
  // 暂时循环删除，后端如有批量接口可替换
  for (const id of selectedIds.value) {
    await deleteFusion(store.currentProjectId, id)
  }
  refreshList()
  selectedIds.value = []
}

// 复制场景
const handleCopyFromScenes = async () => {
  await ElMessageBox.confirm('确定从场景列表复制？这将覆盖当前列表。', '警告', { type: 'warning' })
  loadingStore.start('正在复制...', '请稍候')
  try {
    if (store.shotList.length === 0) await store.fetchShots()
    
    const newFusions = []
    for (const shot of store.shotList) {
       const elements = (shot.characters || []).map(c => ({
         id: `el_${Date.now()}_${Math.random()}`,
         name: c.name,
         image_url: c.image_url,
         type: 'character',
         character_id: c.id
       }))

       const payload = {
         scene: shot.scene,
         shot_number: shot.shot_number,
         shot_id: shot.id,
         base_image: shot.scene_image || '',
         elements: elements,
         scene_description: shot.scene_description || '',
         visual_description: shot.visual_description || '',
         dialogue: shot.dialogue || ''
       }
       const res = await createFusion(store.currentProjectId, payload)
       newFusions.push(res)
    }
    store.fusionList = newFusions
    ElMessage.success(`复制了 ${newFusions.length} 个任务`)
  } catch (e) {
    console.error(e)
  } finally {
    loadingStore.stop()
  }
}

// 元素操作
const openElementDialog = (row) => {
  currentElementFusion.value = row
  elementDialogVisible.value = true
}

const handleElementSuccess = (updatedFusion) => {
  const idx = store.fusionList.findIndex(f => f.id === updatedFusion.id)
  if (idx !== -1) store.fusionList[idx] = updatedFusion
}

const removeElement = async (row, element) => {
  const newElements = row.elements.filter(e => e.id !== element.id)
  row.elements = newElements
  await updateFusion(store.currentProjectId, row.id, { elements: newElements })
}

// 底图上传
const handleBaseUpload = async (row, file) => {
  loadingStore.start('上传中', '正在上传底图...')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('fusion_id', row.id)

  try {
    const res = await uploadBaseImage(fd)
    if (res.success) {
      await updateFusion(store.currentProjectId, row.id, { base_image: res.url })
      row.base_image = res.url
      ElMessage.success('上传成功')
    }
  } catch (err) {
    console.error(err)
  } finally {
    loadingStore.stop()
  }
}

const handleDeleteBaseImage = async (row) => {
  await updateFusion(store.currentProjectId, row.id, { base_image: '' })
  row.base_image = ''
}

// 首帧上传
const handleResultUpload = async (row, file) => {
  loadingStore.start('上传中', '正在上传首帧...')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('fusion_id', row.id)

  try {
    // 复用上传接口
    const res = await uploadBaseImage(fd)
    if (res.success) {
      await updateFusion(store.currentProjectId, row.id, { result_image: res.url })
      row.result_image = res.url
      ElMessage.success('首帧上传成功')
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('上传失败')
  } finally {
    loadingStore.stop()
  }
}

const handleDeleteResultImage = async (row) => {
  await updateFusion(store.currentProjectId, row.id, { result_image: '' })
  row.result_image = ''
}

// 尾帧上传
const handleEndFrameUpload = async (row, file) => {
  loadingStore.start('上传中', '正在上传尾帧...')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('fusion_id', row.id)

  try {
    const res = await uploadBaseImage(fd)
    if (res.success) {
      await updateFusion(store.currentProjectId, row.id, { end_frame_image: res.url })
      row.end_frame_image = res.url
      ElMessage.success('尾帧上传成功')
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('上传失败')
  } finally {
    loadingStore.stop()
  }
}

const handleDeleteEndFrameImage = async (row) => {
  await updateFusion(store.currentProjectId, row.id, { end_frame_image: '' })
  row.end_frame_image = ''
}

const handleDeleteVideo = async (row) => {
  await ElMessageBox.confirm('确定删除视频?')
  await updateFusion(store.currentProjectId, row.id, { video_url: '' })
  row.video_url = ''
  ElMessage.success('视频已删除')
}

const triggerBaseUpload = (row) => {
  uploadTargetRow.value = row
  fileInput.value.click()
}

const handleFileSelected = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  if (uploadTargetRow.value) {
    await handleBaseUpload(uploadTargetRow.value, file)
  }
  e.target.value = ''
}

// 批量操作
const openBatchDialog = (type) => {
  batchType.value = type
  batchDialogVisible.value = true
}

const handleBatchConfirm = async ({ scope, target }) => {
  let tasks = []
  if (scope === 'all') tasks = store.fusionList
  else if (scope === 'selected') tasks = getSelectedItems()
  else if (scope === 'missing') {
    if (target === 'prompt') tasks = store.fusionList.filter(f => !f.fusion_prompt)
    else if (target === 'image') tasks = store.fusionList.filter(f => !f.result_image)
    else if (target === 'end_image') tasks = store.fusionList.filter(f => !f.end_frame_image)
    else if (target === 'video') tasks = store.fusionList.filter(f => !f.video_url)
  }

  if (tasks.length === 0) return ElMessage.warning('没有符合条件的任务')

  let count = 0
  for (const task of tasks) {
    if (target === 'prompt') await generatePrompt(task, true)
    else if (target === 'image') await generateImage(task, true)
    else if (target === 'end_image') await generateEndImage(task, true)
    else if (target === 'video') await generateVideo(task, true)
    count++
  }
  
  if (count > 0) {
    ElNotification.success({ title: '批量任务提交', message: `已提交 ${count} 个任务至后台` })
  }
}

// 生成操作
const generatePrompt = async (row, silent = false) => {
  if (!store.genOptions.textProviderId) return !silent && ElMessage.warning('请选择文本模型')
  
  let mapping = (row.elements || []).map((e, i) => `图${i+1}: ${e.name}`).join('\n')
  if (row.base_image) mapping += '\n底图: Background'

  try {
    await apiGenPrompt({
      id: row.id,
      project_id: store.currentProjectId,
      scene_description: row.scene_description,
      shot_description: row.visual_description,
      element_mapping: mapping,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    if (!silent) ElMessage.success('提示词任务已提交')
  } catch (e) { console.error(e) }
}

const generateImage = async (row, silent = false) => {
  if (!store.genOptions.fusionProviderId) return !silent && ElMessage.warning('请选择图生图模型')
  if (!row.base_image) return !silent && ElMessage.warning('需要底图')
  
  try {
    await apiGenImage({
      fusion_id: row.id,
      project_id: store.currentProjectId,
      fusion_prompt: row.fusion_prompt,
      provider_id: store.genOptions.fusionProviderId,
      model_name: store.genOptions.fusionModelName
    })
    if (!silent) ElMessage.success('首帧任务已提交')
  } catch (e) { console.error(e) }
}

const generateEndImage = async (row, silent = false) => {
  if (!store.genOptions.fusionProviderId) return !silent && ElMessage.warning('请选择图生图模型')
  
  try {
    await apiGenImage({
      fusion_id: row.id,
      project_id: store.currentProjectId,
      fusion_prompt: row.end_frame_prompt,
      end_frame_prompt: row.end_frame_prompt,
      provider_id: store.genOptions.fusionProviderId,
      model_name: store.genOptions.fusionModelName
    })
    if (!silent) ElMessage.success('尾帧任务已提交')
  } catch (e) { console.error(e) }
}

const generateVideo = async (row, silent = false) => {
  if (!store.genOptions.videoProviderId) return !silent && ElMessage.warning('请选择视频模型')
  if (!row.result_image) return !silent && ElMessage.warning('需要首帧图片')

  try {
    await apiGenVideo({
      fusion_id: row.id,
      project_id: store.currentProjectId,
      provider_id: store.genOptions.videoProviderId,
      model_name: store.genOptions.videoModelName
    })
    if (!silent) ElMessage.success('视频任务已提交')
  } catch (e) { console.error(e) }
}

const playVideo = (url) => {
  currentVideoUrl.value = url
  videoPreviewVisible.value = true
}
</script>

<style scoped>
/* 卡片样式 */
.fusion-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  display: grid;
  grid-template-columns: 60px 1fr 640px; /* 调整后的列宽 */
  gap: 16px;
  padding: 0;
  transition: all 0.2s ease;
  position: relative;
  min-height: 240px; /* 增加最小高度以适应内容 */
}

.fusion-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: #d1d5db;
  transform: translateY(-1px);
}

/* 1. 索引区 */
.index-section {
  background-color: #f9fafb;
  border-right: 1px solid #f3f4f6;
  border-top-left-radius: 8px;
  border-bottom-left-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 0;
  cursor: pointer;
}

.scene-badge, .shot-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.label {
  font-size: 10px;
  color: #9ca3af;
  text-transform: uppercase;
}

.value {
  font-size: 18px;
  font-weight: 800;
  color: #374151;
  line-height: 1.2;
}

.divider-vertical {
  width: 20px;
  height: 1px;
  background-color: #e5e7eb;
  margin: 6px 0;
}

/* 2. 内容区 */
.content-section {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  /* justify-content: center; */ /* 允许内容自然撑开 */
}

/* 3. 结果区 */
.result-section {
  padding: 12px;
  border-left: 1px dashed #f3f4f6;
  background-color: #fcfcfc;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  display: flex;
  align-items: center;
}

.hidden { display: none; }

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