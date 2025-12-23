<template>
  <div class="scene-tab h-full flex flex-col bg-gray-50">
    <!-- 顶部配置栏 -->
    <div class="bg-white px-6 py-3 border-b border-gray-200 flex justify-between items-center shadow-sm z-10 shrink-0">
      <div class="flex flex-wrap gap-4 items-center">
        <ModelSelector 
          type="text" 
          label="文本模型" 
          v-model:provider="store.genOptions.textProviderId" 
          v-model:model="store.genOptions.textModelName" 
        />
        <div class="w-px h-6 bg-gray-200 hidden md:block"></div>
        <ModelSelector 
          type="image" 
          label="图片模型" 
          v-model:provider="store.genOptions.imageProviderId" 
          v-model:model="store.genOptions.imageModelName" 
        />
      </div>

      <div class="flex gap-2">
        <el-dropdown split-button type="success" size="small" @click="batchGeneratePrompt" @command="handleBatchCommand">
          批量生成
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="prompt">批量生成提示词</el-dropdown-item>
              <el-dropdown-item command="image">批量生成图片</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- <el-button type="danger" plain size="small" :icon="Delete" :disabled="selectedRows.length === 0" @click="handleBatchDelete">批量删除</el-button> -->
        <!-- <el-button type="danger" plain size="small" :icon="DeleteFilled" @click="handleClearAll">清空全部</el-button> -->
        <!-- <el-button type="primary" size="small" :icon="Plus" @click="openCreateDialog">添加场景</el-button> -->
      </div>
    </div>

    <!-- 自定义表头 -->
    <div class="grid grid-cols-[60px_1fr_200px_180px] gap-4 px-6 py-2 bg-gray-100/80 text-xs font-medium text-gray-500 border-b border-gray-200 shrink-0 select-none">
      <div class="text-center">场次</div>
      <div class="pl-2">场景描述 & 提示词</div>
      <div>场景图片</div>
      <div class="text-right pr-2">出席人物</div>
    </div>

    <!-- 场景列表区域 -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
      <div 
        v-for="(item, index) in store.shotList" 
        :key="item.id" 
        class="scene-card group relative"
      >
        <!-- 1. 索引区块 -->
        <div class="index-section">
          <div class="scene-badge">
            <span class="label">场</span>
            <span class="value">{{ item.scene }}</span>
          </div>
        </div>

        <!-- 2. 内容详情区块 -->
        <div class="content-section">
          <!-- 场景说明 -->
          <div class="content-row mb-3">
            <el-icon class="icon desc"><Document /></el-icon>
            <div class="text-content">
              <span class="label">说明：</span>
              <span class="text-gray-800 font-medium">{{ item.scene_description || '暂无场景说明' }}</span>
            </div>
          </div>
          
          <!-- 场景提示词 -->
          <div class="content-row">
            <el-icon class="icon prompt"><MagicStick /></el-icon>
            <div class="text-content w-full">
              <span class="label">提示词：</span>
              <div class="text-xs text-gray-500 bg-gray-50 p-2 rounded border border-gray-100 mt-1 font-mono break-all leading-relaxed">
                {{ item.scene_prompt || '暂无提示词，请先生成' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 3. 图片区块 -->
        <div class="image-section">
          <UnifiedImageCard
            :src="item.scene_image"
            width="160px"
            height="100px"
            fit="cover"
            placeholder="场景图"
            :show-empty-actions="false"
            :enable-delete="!!item.scene_image"
            custom-class="mx-auto shadow-sm"
            @generate="genImage(item)"
            @upload="(file) => handleSceneUpload(item, file)"
            @delete="handleDeleteImage(item)"
            @click-empty="triggerUpload(item)"
          />
        </div>

        <!-- 4. 人物区块 -->
        <div class="meta-section">
          <div class="characters">
            <el-tag 
              v-for="char in getCharacterObjects(item.characters)" 
              :key="char.id" 
              size="small" 
              type="info" 
              effect="plain"
              class="mb-1 mr-1"
            >
              {{ char.name }}
            </el-tag>
            <span v-if="!item.characters?.length" class="text-xs text-gray-300 italic">无出席人物</span>
          </div>
        </div>

        <!-- 悬浮操作栏 -->
        <div class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 bg-white/90 p-1 rounded shadow-sm border border-gray-100 backdrop-blur-sm z-10">
           <el-tooltip content="编辑" placement="top">
             <el-button type="primary" circle size="small" :icon="Edit" @click.stop="openEditDialog(item)" />
           </el-tooltip>
           
           <!-- 智能生成按钮 -->
           <el-tooltip :content="item.scene_prompt ? '生成图片' : '生成提示词'" placement="top">
             <el-button 
               :type="item.scene_prompt ? 'success' : 'warning'" 
               circle 
               size="small" 
               :icon="item.scene_prompt ? Picture : MagicStick" 
               @click.stop="handleOneClickGenerate(item)" 
             />
           </el-tooltip>

           <!-- <el-tooltip content="向下插入" placement="top">
             <el-button type="success" circle size="small" :icon="Plus" @click.stop="insertScene(index)" />
           </el-tooltip>
           <el-tooltip content="删除" placement="top">
             <el-button type="danger" circle size="small" :icon="Delete" @click.stop="handleDelete(item)" />
           </el-tooltip> -->
        </div>
      </div>

      <el-empty v-if="store.shotList.length === 0" description="暂无场景数据，请添加" />
    </div>

    <!-- 编辑/新建弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="editingId ? '编辑场景' : '添加场景'" 
      width="600px" 
      destroy-on-close
    >
      <el-form :model="form" label-width="90px" size="default">
        <!-- 场次 -->
        <el-form-item label="场次" required>
          <el-input v-model="form.scene" placeholder="例如: 1" />
        </el-form-item>

        <el-form-item label="场景说明">
          <el-input v-model="form.scene_description" type="textarea" :rows="3" placeholder="描述发生了什么..." />
        </el-form-item>

        <el-form-item label="提示词">
          <div class="flex flex-col gap-2 w-full">
            <el-input v-model="form.scene_prompt" type="textarea" :rows="5" placeholder="AI 生成的提示词（也可手动修改）" />
            <div class="text-right">
              <el-button type="success" link :icon="MagicStick" size="small" @click="genPromptForForm">
                立即生成提示词
              </el-button>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="出席人物">
          <el-select 
            v-model="form.characters" 
            multiple 
            placeholder="选择人物" 
            class="w-full"
            collapse-tags
            collapse-tags-tooltip
          >
            <el-option 
              v-for="char in store.characterList" 
              :key="char.id" 
              :label="char.name" 
              :value="char.id" 
            />
          </el-select>
        </el-form-item>

        <el-form-item label="场景图">
          <div class="flex items-center gap-4">
            <UnifiedImageCard
              :src="form.scene_image"
              width="160px"
              height="100px"
              fit="cover"
              placeholder="场景图"
              :enable-delete="!!form.scene_image"
              @generate="genImageForForm"
              @upload="handleFormImageUpload"
              @delete="form.scene_image = ''"
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 隐藏的上传 input -->
    <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="handleFileSelected" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import ModelSelector from '@/components/ModelSelector.vue'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue' 
import { 
  getShots, createShot, updateShot, deleteShot, batchDeleteShots 
} from '@/api/project'
import { 
  generateScenePrompt, generateSceneImage, uploadSceneImage 
} from '@/api/generation'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Plus, Delete, DeleteFilled, Edit, MagicStick, Document, Picture } from '@element-plus/icons-vue'

const store = useProjectStore()
const loadingStore = useLoadingStore()

// --- State ---
const selectedRows = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const insertIndex = ref(-1)

const form = ref({
  scene: '',
  shot_number: '1', 
  scene_description: '',
  scene_prompt: '',
  scene_image: '',
  characters: []
})

const fileInput = ref(null)
const uploadTargetRow = ref(null)

// --- Initialization ---

onMounted(() => {
  if (store.currentProjectId) {
    refreshList()
  }
})

const refreshList = async () => {
  store.loading.shots = true
  try {
    const res = await getShots(store.currentProjectId)
    store.shotList = res || []
  } finally {
    store.loading.shots = false
  }
}

// --- Helpers ---

const getCharacterObjects = (chars) => {
  if (!chars || chars.length === 0) return []
  if (typeof chars[0] === 'object') return chars
  return store.characterList.filter(c => chars.includes(c.id))
}

// --- Actions: List Operations ---

const handleSelectionChange = (val) => {
  selectedRows.value = val
}

const resetForm = () => {
  form.value = {
    scene: '', 
    shot_number: '1', 
    scene_description: '', scene_prompt: '', scene_image: '',
    characters: []
  }
}

const openCreateDialog = () => {
  editingId.value = null
  insertIndex.value = -1
  resetForm()
  // 智能填充场次
  if (store.shotList.length > 0) {
    const last = store.shotList[store.shotList.length - 1]
    const lastSceneNum = parseInt(last.scene)
    if (!isNaN(lastSceneNum)) {
      form.value.scene = String(lastSceneNum + 1)
    } else {
      form.value.scene = last.scene 
    }
  } else {
    form.value.scene = '1'
  }
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  editingId.value = row.id
  insertIndex.value = -1
  const copy = JSON.parse(JSON.stringify(row))
  if (copy.characters && copy.characters.length > 0 && typeof copy.characters[0] === 'object') {
    copy.characters = copy.characters.map(c => c.id)
  }
  if (!copy.shot_number) copy.shot_number = '1'
  form.value = copy
  dialogVisible.value = true
}

const insertScene = (index) => {
  editingId.value = null
  insertIndex.value = index + 1
  resetForm()
  // 插入：尝试让场次 + 1
  const prev = store.shotList[index]
  if (prev) {
    const prevSceneNum = parseInt(prev.scene)
    if (!isNaN(prevSceneNum)) {
      form.value.scene = String(prevSceneNum + 1)
    } else {
      form.value.scene = prev.scene
    }
  }
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm('确定删除该场景?')
  await deleteShot(store.currentProjectId, row.id)
  refreshList()
}

const handleBatchDelete = async () => {
  await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个场景?`)
  const ids = selectedRows.value.map(r => r.id)
  await batchDeleteShots(store.currentProjectId, ids)
  refreshList()
  selectedRows.value = []
}

const handleClearAll = async () => {
  if (store.shotList.length === 0) return
  await ElMessageBox.confirm('确定清空所有场景? 此操作不可恢复。', '警告', { type: 'warning' })
  const ids = store.shotList.map(r => r.id)
  await batchDeleteShots(store.currentProjectId, ids)
  store.shotList = []
}

// --- Actions: Form Submit ---

const submitForm = async () => {
  if (!form.value.scene) {
    return ElMessage.warning('场次必填')
  }
  
  const payload = { ...form.value }
  if (!payload.shot_number) payload.shot_number = '1'
  
  try {
    if (editingId.value) {
      const res = await updateShot(store.currentProjectId, editingId.value, payload)
      const idx = store.shotList.findIndex(s => s.id === editingId.value)
      if (idx !== -1) {
        res.characters = getCharacterObjects(res.characters || payload.characters)
        store.shotList[idx] = res
      }
    } else {
      if (insertIndex.value > -1) payload.insert_index = insertIndex.value
      const res = await createShot(store.currentProjectId, payload)
      res.characters = getCharacterObjects(res.characters || payload.characters)
      
      if (insertIndex.value > -1) store.shotList.splice(insertIndex.value, 0, res)
      else store.shotList.push(res)
    }
    dialogVisible.value = false
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
  }
}

// --- Actions: Generation ---

// 智能生成按钮逻辑：串联生成
const handleOneClickGenerate = async (row) => {
  // 1. 如果已有提示词，直接生成图片
  if (row.scene_prompt) {
    if (row.scene_image) {
      try {
        await ElMessageBox.confirm('已有图片，确定重新生成吗？', '提示', { type: 'warning' })
      } catch { return }
    }
    await genImage(row)
    return
  }

  // 2. 如果没有提示词，开始“生成词 -> 等待 -> 生成图”流程
  await genPrompt(row)
  
  // 开启轮询
  const checkInterval = setInterval(() => {
    const currentItem = store.shotList.find(item => item.id === row.id)
    
    if (currentItem && currentItem.scene_prompt) {
      clearInterval(checkInterval)
      ElNotification.success({ title: '提示词已就绪', message: `场景 ${row.scene} 自动开始生成图片...` })
      genImage(currentItem)
    }
  }, 2000)

  // 60秒超时保护
  setTimeout(() => {
    clearInterval(checkInterval)
  }, 60000)
  
  ElMessage.success('已启动全流程生成：正在生成提示词，完成后将自动生成图片。')
}

const genPrompt = async (row) => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请先选择文本模型')
  if (!row.scene_description) return ElMessage.warning('请先填写场景说明')
  
  try {
    await generateScenePrompt({
      scene_id: row.id,
      project_id: store.currentProjectId,
      scene_description: row.scene_description,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
  } catch (e) { console.error(e) }
}

const genImage = async (row) => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请先选择图片模型')
  if (!row.scene_prompt) return ElMessage.warning('请先生成提示词')
  
  try {
    await generateSceneImage({
      scene_id: row.id,
      project_id: store.currentProjectId,
      scene_prompt: row.scene_prompt,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
  } catch (e) { console.error(e) }
}

const genPromptForForm = async () => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请先选择文本模型')
  if (!form.value.scene_description) return ElMessage.warning('请填写场景说明')
  
  if (!editingId.value) return ElMessage.warning('请先保存场景，再使用 AI 生成')

  await generateScenePrompt({
    scene_id: editingId.value,
    project_id: store.currentProjectId,
    scene_description: form.value.scene_description,
    provider_id: store.genOptions.textProviderId,
    model_name: store.genOptions.textModelName
  })
  ElNotification.info({ title: '提示', message: '生成任务后台运行中，结果稍后会自动更新' })
}

const genImageForForm = async () => {
  if (!editingId.value) return ElMessage.warning('请先保存场景')
  if (!form.value.scene_prompt) return ElMessage.warning('缺少提示词')
  
  await generateSceneImage({
    scene_id: editingId.value,
    project_id: store.currentProjectId,
    scene_prompt: form.value.scene_prompt,
    provider_id: store.genOptions.imageProviderId,
    model_name: store.genOptions.imageModelName
  })
  ElMessage.success('任务已提交')
}

// --- Actions: Batch Generation ---

const handleBatchCommand = (cmd) => {
  if (cmd === 'prompt') batchGeneratePrompt()
  else batchGenerateImage()
}

const batchGeneratePrompt = async () => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请选择文本模型')
  const targets = store.shotList.filter(s => s.scene_description && !s.scene_prompt)
  if (targets.length === 0) return ElMessage.info('没有需要生成的场景')

  let count = 0
  for (const t of targets) {
    await generateScenePrompt({
      scene_id: t.id,
      project_id: store.currentProjectId,
      scene_description: t.scene_description,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    count++
  }
  if (count > 0) ElNotification.success({ title: '批量提交', message: `已提交 ${count} 个提示词任务` })
}

const batchGenerateImage = async () => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请选择图片模型')
  const targets = store.shotList.filter(s => s.scene_prompt && !s.scene_image)
  if (targets.length === 0) return ElMessage.info('没有需要生成的场景')

  let count = 0
  for (const t of targets) {
    await generateSceneImage({
      scene_id: t.id,
      project_id: store.currentProjectId,
      scene_prompt: t.scene_prompt,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    count++
  }
  if (count > 0) ElNotification.success({ title: '批量提交', message: `已提交 ${count} 个生图任务` })
}

// --- Actions: Upload ---

const handleSceneUpload = async (row, file) => {
  loadingStore.start('上传中', '正在上传场景图片...')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('scene_id', row.id)

  try {
    const res = await uploadSceneImage(fd)
    if (res.success) {
      await updateShot(store.currentProjectId, row.id, { scene_image: res.url })
      row.scene_image = res.url
      ElMessage.success('上传并保存成功')
    }
  } catch (err) {
    console.error(err)
  } finally {
    loadingStore.stop()
  }
}

const handleFormImageUpload = async (file) => {
  if (!editingId.value) return ElMessage.warning('请先保存场景')
  
  loadingStore.start('上传中', '正在上传场景图片...')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('scene_id', editingId.value)

  try {
    const res = await uploadSceneImage(fd)
    if (res.success) {
      await updateShot(store.currentProjectId, editingId.value, { scene_image: res.url })
      form.value.scene_image = res.url
      const idx = store.shotList.findIndex(s => s.id === editingId.value)
      if (idx !== -1) store.shotList[idx].scene_image = res.url
      ElMessage.success('上传并保存成功')
    }
  } catch (err) {
    console.error(err)
  } finally {
    loadingStore.stop()
  }
}

const handleDeleteImage = async (row) => {
  await ElMessageBox.confirm('确定删除该场景图片?')
  await updateShot(store.currentProjectId, row.id, { scene_image: '' })
  row.scene_image = ''
  ElMessage.success('图片已删除')
}

const triggerUpload = (row) => {
  uploadTargetRow.value = row
  fileInput.value.click()
}

const handleFileSelected = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  if (uploadTargetRow.value) {
    await handleSceneUpload(uploadTargetRow.value, file)
  }
  e.target.value = ''
}
</script>

<style scoped>
/* 卡片基础样式 */
.scene-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  display: grid;
  grid-template-columns: 60px 1fr 200px 180px; /* 定义四列布局：移除镜号列 */
  gap: 16px;
  padding: 0;
  transition: all 0.2s ease;
  position: relative;
  min-height: 120px;
}

.scene-card:hover {
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
}

.scene-badge {
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

/* 2. 内容区 */
.content-section {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.content-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.icon {
  margin-top: 3px;
  font-size: 14px;
  flex-shrink: 0;
}
.icon.desc { color: #6b7280; }
.icon.prompt { color: #8b5cf6; }

.text-content {
  font-size: 13px;
  line-height: 1.5;
  color: #1f2937;
}

.text-content .label {
  color: #9ca3af;
  margin-right: 4px;
}

/* 3. 图片区 */
.image-section {
  padding: 12px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 4. 元数据区 */
.meta-section {
  padding: 16px 16px 16px 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 8px;
}

.characters {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 100%;
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