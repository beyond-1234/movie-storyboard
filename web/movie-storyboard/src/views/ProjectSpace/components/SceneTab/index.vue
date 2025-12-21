<template>
  <div class="scene-tab h-full flex flex-col">
    <!-- 顶部配置栏 -->
    <div class="bg-white p-3 rounded shadow-sm mb-4 flex flex-wrap gap-4 items-center justify-between">
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
        <el-dropdown split-button size="small" @click="batchGeneratePrompt" @command="handleBatchCommand">
          批量生成
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="prompt">批量生成提示词</el-dropdown-item>
              <el-dropdown-item command="image">批量生成图片</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button type="danger" plain size="small" icon="Delete" :disabled="selectedRows.length === 0" @click="handleBatchDelete">批量删除</el-button>
        <el-button type="danger" plain size="small" icon="DeleteFilled" @click="handleClearAll">清空全部</el-button>
        <el-button type="primary" plain size="small" icon="Plus" @click="openCreateDialog">添加场景</el-button>
      </div>
    </div>

    <!-- 场景列表 -->
    <el-table 
      :data="store.shotList" 
      v-loading="store.loading.shots" 
      border 
      stripe 
      row-key="id"
      class="flex-1"
      height="100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="scene" label="场次" width="70" align="center" sortable />
      <el-table-column prop="shot_number" label="镜号" width="70" align="center" sortable />
      
      <el-table-column label="场景说明" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="whitespace-pre-wrap text-sm">{{ row.scene_description }}</div>
        </template>
      </el-table-column>
      
      <el-table-column label="场景提示词" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="text-xs text-gray-500 font-mono">{{ row.scene_prompt || '暂无提示词' }}</div>
        </template>
      </el-table-column>

      <el-table-column label="场景图片" width="140" align="center">
        <template #default="{ row }">
          <div class="relative w-24 h-16 bg-gray-100 border rounded flex items-center justify-center group overflow-hidden mx-auto">
            <el-image 
              v-if="row.scene_image" 
              :src="row.scene_image" 
              class="w-full h-full" 
              fit="cover" 
              :preview-src-list="[row.scene_image]" 
              hide-on-click-modal
            />
            <div v-else class="text-xs text-gray-400 flex flex-col items-center">
              <el-icon><Picture /></el-icon>
            </div>
            
            <!-- 悬浮操作 -->
            <div class="absolute inset-0 bg-black/60 hidden group-hover:flex items-center justify-center gap-2">
               <el-tooltip content="生成图片" placement="top">
                 <el-button type="success" circle size="small" icon="MagicStick" @click="genImage(row)" />
               </el-tooltip>
               <el-tooltip content="上传替换" placement="top">
                 <el-button type="primary" circle size="small" icon="Upload" @click="triggerUpload(row)" />
               </el-tooltip>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="出席人物" width="150">
        <template #default="{ row }">
          <div class="flex flex-wrap gap-1">
            <!-- 兼容逻辑：characters 可能是对象数组，也可能是 ID 数组 -->
            <el-tag 
              v-for="char in getCharacterObjects(row.characters)" 
              :key="char.id" 
              size="small" 
              effect="plain"
            >
              {{ char.name }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row, $index }">
          <div class="flex flex-wrap gap-1 justify-center">
            <el-tooltip content="编辑" placement="top"><el-button size="small" icon="Edit" circle @click="openEditDialog(row)" /></el-tooltip>
            <el-tooltip content="生成提示词" placement="top"><el-button size="small" type="warning" plain icon="MagicStick" circle @click="genPrompt(row)" /></el-tooltip>
            <el-tooltip content="删除" placement="top"><el-button size="small" type="danger" plain icon="Delete" circle @click="handleDelete(row)" /></el-tooltip>
            <el-tooltip content="向下插入" placement="top"><el-button size="small" type="primary" plain icon="Plus" circle @click="insertScene($index)" /></el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑/新建弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="editingId ? '编辑场景' : '添加场景'" 
      width="600px" 
      destroy-on-close
    >
      <el-form :model="form" label-width="90px" size="default">
        <div class="flex gap-4">
          <el-form-item label="场次" required class="flex-1">
            <el-input v-model="form.scene" placeholder="1" />
          </el-form-item>
          <el-form-item label="镜号" required class="flex-1">
            <el-input v-model="form.shot_number" placeholder="1" />
          </el-form-item>
        </div>

        <el-form-item label="场景说明">
          <el-input v-model="form.scene_description" type="textarea" :rows="3" placeholder="描述发生了什么..." />
        </el-form-item>

        <el-form-item label="提示词">
          <div class="flex flex-col gap-2 w-full">
            <el-input v-model="form.scene_prompt" type="textarea" :rows="5" placeholder="AI 生成的提示词（也可手动修改）" />
            <div class="text-right">
              <el-button type="success" link icon="MagicStick" size="small" @click="genPromptForForm">
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
            <div v-if="form.scene_image" class="w-32 h-20 border rounded overflow-hidden relative group">
              <el-image :src="form.scene_image" class="w-full h-full" fit="cover" />
              <div class="absolute inset-0 bg-black/50 hidden group-hover:flex items-center justify-center cursor-pointer text-white" @click="form.scene_image = ''">
                 <el-icon><Delete /></el-icon>
              </div>
            </div>
            <div class="flex flex-col gap-2">
              <el-button size="small" icon="Upload" @click="triggerUploadForForm">上传图片</el-button>
              <el-button size="small" type="success" plain icon="MagicStick" @click="genImageForForm">生成图片</el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" plain @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 隐藏的上传 input -->
    <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="handleFileSelected" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import ModelSelector from '@/components/ModelSelector.vue'
import { 
  getShots, createShot, updateShot, deleteShot, batchDeleteShots 
} from '@/api/project'
import { 
  generateScenePrompt, generateSceneImage, uploadSceneImage 
} from '@/api/generation'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

const store = useProjectStore()
const loadingStore = useLoadingStore()

// --- State ---
const selectedRows = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const insertIndex = ref(-1) // 插入位置索引

const form = ref({
  scene: '',
  shot_number: '',
  scene_description: '',
  scene_prompt: '',
  scene_image: '',
  characters: [] // 这里存储 ID 数组
})

const fileInput = ref(null)
const uploadContext = ref(null) // 'list' | 'form'
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

// 统一处理角色对象获取（兼容 API 返回的是 ID 还是对象）
const getCharacterObjects = (chars) => {
  if (!chars || chars.length === 0) return []
  // 如果是对象数组，直接返回
  if (typeof chars[0] === 'object') return chars
  // 如果是 ID 数组，去 store 里找
  return store.characterList.filter(c => chars.includes(c.id))
}

// --- Actions: List Operations ---

const handleSelectionChange = (val) => {
  selectedRows.value = val
}

const openCreateDialog = () => {
  editingId.value = null
  insertIndex.value = -1
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  editingId.value = row.id
  insertIndex.value = -1
  // Deep copy & format characters to IDs
  const copy = JSON.parse(JSON.stringify(row))
  if (copy.characters && copy.characters.length > 0 && typeof copy.characters[0] === 'object') {
    copy.characters = copy.characters.map(c => c.id)
  }
  form.value = copy
  dialogVisible.value = true
}

const insertScene = (index) => {
  editingId.value = null
  insertIndex.value = index + 1
  resetForm()
  // 智能填充：尝试自动+1镜号
  const prev = store.shotList[index]
  if (prev) {
    form.value.scene = prev.scene
    // 尝试解析数字并+1
    const num = parseInt(prev.shot_number)
    if (!isNaN(num)) form.value.shot_number = String(num + 1)
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

const resetForm = () => {
  form.value = {
    scene: '', shot_number: '',
    scene_description: '', scene_prompt: '', scene_image: '',
    characters: []
  }
}

const submitForm = async () => {
  if (!form.value.scene || !form.value.shot_number) {
    return ElMessage.warning('场次和镜号必填')
  }

  // 构造提交数据
  // 注意：后端可能期望 characters 是对象数组或 ID 数组，这里根据 API 定义
  // 如果后端 project.js 里的 createShot 能处理 ID 数组最好。
  // 这里我们提交前，把 ID 数组转回对象数组，或者让后端处理。
  // 通常 CRUD 接口传 ID 比较规范。假设后端接受 ID 数组。
  
  const payload = { ...form.value }
  // 确保字符是 ID 数组
  
  try {
    if (editingId.value) {
      // Update
      const res = await updateShot(store.currentProjectId, editingId.value, payload)
      // 手动更新本地列表
      const idx = store.shotList.findIndex(s => s.id === editingId.value)
      if (idx !== -1) {
        // 更新时，为了显示人名，我们需要把 characters ID 换成对象
        res.characters = getCharacterObjects(res.characters || payload.characters)
        store.shotList[idx] = res
      }
    } else {
      // Create
      if (insertIndex.value > -1) {
        payload.insert_index = insertIndex.value
      }
      const res = await createShot(store.currentProjectId, payload)
      // 填充角色对象用于显示
      res.characters = getCharacterObjects(res.characters || payload.characters)
      
      if (insertIndex.value > -1) {
        store.shotList.splice(insertIndex.value, 0, res)
      } else {
        store.shotList.push(res)
      }
    }
    dialogVisible.value = false
    ElMessage.success('保存成功')
  } catch (e) {
    console.error(e)
  }
}

// --- Actions: Generation (List context) ---

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
    ElMessage.success('提示词生成任务已提交')
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
    ElMessage.success('图片生成任务已提交')
  } catch (e) { console.error(e) }
}

// --- Actions: Generation (Form context) ---

const genPromptForForm = async () => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请先选择文本模型')
  if (!form.value.scene_description) return ElMessage.warning('请填写场景说明')
  
  // 如果是新建场景，还没 ID，不能用异步任务回调更新。
  // 这种情况下，要么先保存，要么使用同步接口（如果有）。
  // 这里假设必须先保存。
  if (!editingId.value) {
    return ElMessage.warning('请先保存场景，再使用 AI 生成')
  }

  // 调用生成接口
  await generateScenePrompt({
    scene_id: editingId.value,
    project_id: store.currentProjectId,
    scene_description: form.value.scene_description,
    provider_id: store.genOptions.textProviderId,
    model_name: store.genOptions.textModelName
  })
  
  // 只是提交了任务，弹窗里无法立即看到。
  // 可以在这里提示用户“任务已提交，完成后请刷新”。
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
  
  // 筛选没提示词的
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

const triggerUpload = (row) => {
  uploadContext.value = 'list'
  uploadTargetRow.value = row
  fileInput.value.click()
}

const triggerUploadForForm = () => {
  if (!editingId.value) return ElMessage.warning('请先保存场景')
  uploadContext.value = 'form'
  fileInput.value.click()
}

const handleFileSelected = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  const targetId = uploadContext.value === 'form' ? editingId.value : uploadTargetRow.value?.id
  if (!targetId) return

  loadingStore.start('上传中', '正在上传场景图片...')
  
  const fd = new FormData()
  fd.append('file', file)
  fd.append('scene_id', targetId)

  try {
    const res = await uploadSceneImage(fd)
    if (res.success) {
      if (uploadContext.value === 'form') {
        form.value.scene_image = res.url
      }
      // 更新列表数据
      const idx = store.shotList.findIndex(s => s.id === targetId)
      if (idx !== -1) {
        store.shotList[idx].scene_image = res.url
      }
      ElMessage.success('上传成功')
    }
  } catch (err) {
    console.error(err)
  } finally {
    loadingStore.stop()
    e.target.value = ''
  }
}
</script>