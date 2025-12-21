<template>
  <div class="fusion-tab h-full flex flex-col">
    <!-- 顶部配置栏 -->
    <div class="bg-white p-3 rounded shadow-sm mb-4">
      <div class="flex flex-wrap gap-4 items-center border-b pb-3 mb-3">
        <ModelSelector type="text" label="文本模型" v-model:provider="store.genOptions.textProviderId" v-model:model="store.genOptions.textModelName" />
        <div class="w-px h-6 bg-gray-200 hidden md:block"></div>
        <ModelSelector type="image_fusion" label="图生图模型" v-model:provider="store.genOptions.fusionProviderId" v-model:model="store.genOptions.fusionModelName" />
        <div class="w-px h-6 bg-gray-200 hidden md:block"></div>
        <ModelSelector type="video" label="视频模型" v-model:provider="store.genOptions.videoProviderId" v-model:model="store.genOptions.videoModelName" />
      </div>

      <div class="flex justify-between items-center">
        <div class="flex gap-2">
          <el-button type="danger" plain size="small" icon="Delete" :disabled="selectedRows.length === 0" @click="handleBatchDelete">批量删除</el-button>
          <el-button type="warning" plain size="small" icon="CopyDocument" @click="handleCopyFromScenes">从场景列表复制</el-button>
        </div>
        
        <div class="flex gap-2">
          <el-dropdown split-button type="success" size="small" @click="openBatchDialog('image')" @command="openBatchDialog">
            批量生成融合图
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="prompt">批量生成提示词</el-dropdown-item>
                <el-dropdown-item command="image">批量生成首帧</el-dropdown-item>
                <el-dropdown-item command="end_image">批量生成尾帧</el-dropdown-item>
                <el-dropdown-item command="video" divided>批量生成视频</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button type="primary" size="small" icon="Plus" @click="openCreateDialog">添加任务</el-button>
        </div>
      </div>
    </div>

    <!-- 融图任务列表 -->
    <el-table 
      :data="store.fusionList" 
      v-loading="store.loading.fusions" 
      border 
      stripe 
      row-key="id"
      class="flex-1"
      height="100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column label="场号" width="70">
        <template #default="{ row }">
          <div class="text-center font-bold">{{ row.scene }}-{{ row.shot_number }}</div>
        </template>
      </el-table-column>
      
      <!-- 描述信息 -->
      <el-table-column label="描述信息" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="text-xs">
            <div v-if="row.visual_description"><span class="font-bold text-gray-500">画面:</span> {{ row.visual_description }}</div>
            <div v-if="row.dialogue" class="mt-1 text-blue-600"><span class="font-bold text-gray-500">台词:</span> {{ row.dialogue }}</div>
          </div>
        </template>
      </el-table-column>

      <!-- 底图与元素 -->
      <el-table-column label="底图 & 元素" width="220">
        <template #default="{ row }">
          <div class="flex items-start gap-2 overflow-x-auto pb-1">
            <!-- 底图 -->
            <div class="shrink-0 relative w-16 h-12 bg-gray-100 border rounded flex items-center justify-center">
              <el-image v-if="row.base_image" :src="row.base_image" class="w-full h-full" fit="cover" :preview-src-list="[row.base_image]" />
              <span v-else class="text-[10px] text-gray-400">底图</span>
            </div>
            
            <!-- 元素列表 -->
            <div v-for="el in row.elements" :key="el.id" class="shrink-0 relative w-12 h-12 border rounded group">
              <el-image :src="el.image_url" class="w-full h-full" fit="cover" :preview-src-list="[el.image_url]" />
              <div class="absolute -top-1 -right-1 cursor-pointer hidden group-hover:block z-10" @click.stop="removeElement(row, el)">
                <el-icon class="text-red-500 bg-white rounded-full text-xs border"><CircleClose /></el-icon>
              </div>
              <div class="absolute bottom-0 inset-x-0 bg-black/50 text-white text-[9px] truncate px-1">{{ el.name }}</div>
            </div>
            
            <!-- 添加元素按钮 -->
            <el-button size="small" circle icon="Plus" class="shrink-0" @click="openElementDialog(row)" />
          </div>
        </template>
      </el-table-column>

      <!-- 生成结果 -->
      <el-table-column label="生成结果 (首帧/尾帧/视频)" width="260">
        <template #default="{ row }">
          <div class="flex gap-2 items-center">
            <!-- 首帧 -->
            <div class="relative w-20 h-14 bg-gray-50 border rounded flex items-center justify-center">
              <el-image v-if="row.result_image" :src="row.result_image" class="w-full h-full" fit="cover" :preview-src-list="[row.result_image]" />
              <div v-else class="text-xs text-gray-300">首帧</div>
              <div class="absolute bottom-0 right-0 bg-black/50 text-white text-[9px] px-1">Start</div>
            </div>
            <!-- 尾帧 -->
            <div class="relative w-20 h-14 bg-gray-50 border rounded flex items-center justify-center">
              <el-image v-if="row.end_frame_image" :src="row.end_frame_image" class="w-full h-full" fit="cover" :preview-src-list="[row.end_frame_image]" />
              <div v-else class="text-xs text-gray-300">尾帧</div>
              <div class="absolute bottom-0 right-0 bg-black/50 text-white text-[9px] px-1">End</div>
            </div>
            <!-- 视频播放 -->
             <div 
              v-if="row.video_url"
              class="relative w-20 h-14 bg-black rounded cursor-pointer flex items-center justify-center hover:scale-105 transition-transform"
              @click="playVideo(row.video_url)"
            >
              <video :src="row.video_url" class="w-full h-full object-cover opacity-60"></video>
              <el-icon class="absolute text-white text-xl"><VideoPlay /></el-icon>
            </div>
          </div>
        </template>
      </el-table-column>

      <!-- 操作区 -->
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row, $index }">
          <div class="flex flex-wrap gap-1">
            <el-tooltip content="编辑" placement="top"><el-button size="small" icon="Edit" circle @click="openEditDialog(row)" /></el-tooltip>
            <el-tooltip content="生成提示词" placement="top"><el-button size="small" type="warning" plain icon="MagicStick" circle @click="generatePrompt(row)" /></el-tooltip>
            <el-tooltip content="生成图片" placement="top"><el-button size="small" type="success" plain icon="Picture" circle @click="generateImage(row)" /></el-tooltip>
            <el-tooltip content="生成视频" placement="top"><el-button size="small" type="primary" plain icon="VideoCamera" circle :disabled="!row.result_image" @click="generateVideo(row)" /></el-tooltip>
            <el-tooltip content="删除" placement="top"><el-button size="small" type="danger" plain icon="Delete" circle @click="handleDelete(row)" /></el-tooltip>
             <el-tooltip content="向下插入" placement="top"><el-button size="small" icon="Plus" circle @click="insertFusion($index)" /></el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 弹窗组件 -->
    <FusionEditDialog v-model="editDialogVisible" :initial-data="currentEditingRow" @success="refreshList" />
    <ElementDialog v-model="elementDialogVisible" :fusion="currentElementFusion" @success="handleElementSuccess" />
    <BatchDialog v-model="batchDialogVisible" :type="batchType" :selection="selectedRows" @confirm="handleBatchConfirm" />
    
    <!-- 视频预览 -->
    <el-dialog v-model="videoPreviewVisible" title="视频预览" width="60%" destroy-on-close align-center>
      <video v-if="currentVideoUrl" :src="currentVideoUrl" controls autoplay class="w-full max-h-[70vh]"></video>
    </el-dialog>
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

// === 关键修复：正确的导入路径 ===
import { 
  getFusions, deleteFusion, createFusion, updateFusion
} from '@/api/project' 
import { 
  generateFusionPrompt as apiGenPrompt, // 使用别名以区分本地方法
  generateFusionImage as apiGenImage, 
  generateFusionVideo as apiGenVideo 
} from '@/api/generation'
// =============================

import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

const store = useProjectStore()
const loadingStore = useLoadingStore()

// State
const selectedRows = ref([])
const editDialogVisible = ref(false)
const elementDialogVisible = ref(false)
const batchDialogVisible = ref(false)
const videoPreviewVisible = ref(false)
const currentVideoUrl = ref('')
const currentEditingRow = ref(null)
const currentElementFusion = ref(null)
const batchType = ref('image')

// Initialization
onMounted(() => {
  refreshList()
})

const refreshList = async () => {
  if (!store.currentProjectId) return
  // 确保 store.loading.fusions 存在（即便 store 未更新也能运行）
  if (store.loading) store.loading.fusions = true
  try {
    const res = await getFusions(store.currentProjectId)
    store.fusionList = res || []
  } finally {
    if (store.loading) store.loading.fusions = false
  }
}

// Actions
const handleSelectionChange = (val) => {
  selectedRows.value = val
}

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
  await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个任务?`)
  for (const row of selectedRows.value) {
    await deleteFusion(store.currentProjectId, row.id)
  }
  refreshList()
  selectedRows.value = []
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

// 批量操作
const openBatchDialog = (type) => {
  batchType.value = type
  batchDialogVisible.value = true
}

const handleBatchConfirm = async ({ scope, target }) => {
  let tasks = []
  if (scope === 'all') tasks = store.fusionList
  else if (scope === 'selected') tasks = selectedRows.value
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

// 单个生成操作 (调用 aliased API)
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
    if (!silent) ElMessage.success('提示词生成任务已提交')
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
    if (!silent) ElMessage.success('首帧生成任务已提交')
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
    if (!silent) ElMessage.success('尾帧生成任务已提交')
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
    if (!silent) ElMessage.success('视频生成任务已提交')
  } catch (e) { console.error(e) }
}

const playVideo = (url) => {
  currentVideoUrl.value = url
  videoPreviewVisible.value = true
}
</script>