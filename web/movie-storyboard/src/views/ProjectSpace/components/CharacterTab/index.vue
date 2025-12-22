<template>
  <div class="character-tab h-full flex flex-col">
    <!-- 顶部工具栏 -->
    <div class="bg-white p-4 rounded shadow-sm mb-4 flex flex-wrap gap-4 items-center justify-between">
      <div class="flex flex-wrap gap-4 items-center">
        <!-- 复用模型选择器组件 -->
        <ModelSelector 
          type="image" 
          label="生图模型" 
          v-model:provider="store.genOptions.imageProviderId" 
          v-model:model="store.genOptions.imageModelName" 
        />
        <div class="w-px h-6 bg-gray-200 mx-2 hidden md:block"></div>
        <ModelSelector 
          type="text" 
          label="列表生成模型" 
          v-model:provider="store.genOptions.textProviderId" 
          v-model:model="store.genOptions.textModelName" 
        />
      </div>
      
      <div class="flex gap-3">
        <el-button type="primary" icon="Plus" @click="openCreateDialog">创建角色</el-button>
        <el-button type="success" icon="MagicStick" :loading="generatingList" @click="handleAutoGenerateList">
          从设定生成
        </el-button>
        <el-popconfirm 
          title="确定清空所有角色吗？此操作不可恢复。" 
          confirm-button-type="danger"
          @confirm="handleBatchDelete"
        >
          <template #reference>
            <el-button type="danger" plain icon="Delete" :disabled="store.characterList.length === 0">清空全部</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <!-- 角色列表内容区 -->
    <div class="flex-1 overflow-y-auto pr-2 custom-scrollbar">
      <el-empty v-if="store.characterList.length === 0" description="暂无角色，请点击右上角创建或从设定生成" />
      
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-5">
        <div 
          v-for="char in store.characterList" 
          :key="char.id" 
          class="bg-white rounded-lg border hover:shadow-md transition-shadow flex flex-col overflow-hidden group h-[420px]"
        >
          <!-- 卡片头部 -->
          <div class="p-3 border-b flex justify-between items-center bg-gray-50 shrink-0">
            <span class="font-bold text-gray-700 truncate mr-2 flex-1" :title="char.name">{{ char.name }}</span>
            <el-button 
              type="danger" 
              link 
              icon="Delete" 
              class="opacity-0 group-hover:opacity-100 transition-opacity"
              @click="handleDelete(char)" 
            />
          </div>

          <!-- 图片区域 (替换为 UnifiedImageCard) -->
          <div class="h-64 bg-gray-100 shrink-0">
            <UnifiedImageCard
              :src="char.image_url"
              width="100%"
              height="100%"
              fit="contain"
              custom-class="!border-0 !rounded-none"
              placeholder="暂无角色设计图"
              :show-empty-actions="true"
              @generate="handleGenerateImage(char)"
              @upload="(file) => handleCharacterUpload(char, file)"
              @delete="handleDeleteImage(char)"
            />
          </div>

          <!-- 描述/编辑区域 -->
          <div class="p-4 flex-1 flex flex-col text-sm min-h-0 bg-white relative">
            <div v-if="editingId === char.id" class="flex flex-col gap-2 h-full absolute inset-0 p-4 bg-white z-10">
              <el-input 
                v-model="tempDescription" 
                type="textarea" 
                class="flex-1"
                resize="none" 
                placeholder="输入角色描述..."
              />
              <div class="flex justify-end gap-2 shrink-0">
                <el-button size="small" @click="cancelEdit">取消</el-button>
                <el-button size="small" type="primary" @click="saveDescription(char)">保存</el-button>
              </div>
            </div>
            
            <div v-else class="flex flex-col h-full relative group/desc">
              <div class="text-gray-600 line-clamp-4 leading-relaxed whitespace-pre-wrap overflow-hidden" :title="char.description">
                {{ char.description || '暂无描述' }}
              </div>
              
              <!-- 悬浮编辑按钮 -->
              <div class="absolute bottom-0 right-0 pt-4 bg-gradient-to-t from-white via-white to-transparent w-full flex justify-end opacity-0 group-hover/desc:opacity-100 transition-opacity">
                <el-button type="primary" link size="small" icon="Edit" @click="startEdit(char)">编辑描述</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建角色弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      title="创建新角色" 
      width="500px" 
      destroy-on-close
    >
      <el-form :model="createForm" label-width="80px" @submit.prevent="submitCreate">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" placeholder="例如：孙悟空" autofocus />
        </el-form-item>
        <el-form-item label="外貌描述">
          <el-input 
            v-model="createForm.description" 
            type="textarea" 
            :rows="4" 
            placeholder="描述角色的年龄、长相、服装、性格特征等..." 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import ModelSelector from '@/components/ModelSelector.vue'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue' // 引入通用组件
import { 
  createCharacter, 
  deleteCharacter, 
  batchDeleteCharacters, 
  updateCharacter 
} from '@/api/project'
import { 
  uploadCharacterImage, 
  generateCharacterList, 
  generateCharacterViews 
} from '@/api/generation'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Plus, MagicStick, Delete, Edit } from '@element-plus/icons-vue'

// --- Stores ---
const store = useProjectStore()
const loadingStore = useLoadingStore()

// --- State ---
const dialogVisible = ref(false)
const createForm = ref({ name: '', description: '' })
const creating = ref(false)
const generatingList = ref(false)

// 编辑描述相关状态
const editingId = ref(null)
const tempDescription = ref('')

// --- Methods: CRUD ---

// 打开创建弹窗
const openCreateDialog = () => {
  createForm.value = { name: '', description: '' }
  dialogVisible.value = true
}

// 提交创建
const submitCreate = async () => {
  if (!createForm.value.name) return ElMessage.warning('请输入角色名称')
  
  creating.value = true
  try {
    const newChar = await createCharacter(store.currentProjectId, createForm.value)
    store.characterList.push(newChar) // 更新本地 Store
    ElMessage.success('角色创建成功')
    dialogVisible.value = false
  } catch (error) {
    console.error(error)
  } finally {
    creating.value = false
  }
}

// 删除单个角色
const handleDelete = async (char) => {
  try {
    await ElMessageBox.confirm(`确定要删除角色 "${char.name}" 吗?`, '警告', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    
    await deleteCharacter(store.currentProjectId, char.id)
    // 从本地列表中移除
    store.characterList = store.characterList.filter(c => c.id !== char.id)
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

// 批量清空
const handleBatchDelete = async () => {
  if (store.characterList.length === 0) return
  
  try {
    const ids = store.characterList.map(c => c.id)
    await batchDeleteCharacters(store.currentProjectId, ids)
    store.characterList = []
    ElMessage.success('已清空所有角色')
  } catch (e) {
    console.error(e)
  }
}

// --- Methods: Description Editing ---

const startEdit = (char) => {
  editingId.value = char.id
  tempDescription.value = char.description || ''
}

const cancelEdit = () => {
  editingId.value = null
  tempDescription.value = ''
}

const saveDescription = async (char) => {
  if (tempDescription.value === char.description) {
    cancelEdit()
    return
  }
  
  try {
    // 乐观更新：先改 UI，失败再回滚
    await updateCharacter(store.currentProjectId, char.id, {
      description: tempDescription.value
    })
    
    // 更新本地数据
    char.description = tempDescription.value
    ElMessage.success('描述已更新')
    cancelEdit()
  } catch (e) {
    console.error(e)
  }
}

// --- Methods: Image Handling (Using UnifiedImageCard) ---

// 上传图片处理
const handleCharacterUpload = async (char, file) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('character_id', char.id)

  loadingStore.start('图片上传中', '正在处理您的图片...')
  
  try {
    const res = await uploadCharacterImage(formData)
    if (res.success && res.url) {
      // 1. 调用更新接口，持久化到数据库
      await updateCharacter(store.currentProjectId, char.id, { image_url: res.url })
      
      // 2. 更新本地状态
      char.image_url = res.url 
      ElMessage.success('上传并保存成功')
    } else {
      ElMessage.error(res.error || '上传失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('上传出错')
  } finally {
    loadingStore.stop()
  }
}

// 删除图片处理
const handleDeleteImage = async (char) => {
  try {
    await ElMessageBox.confirm('确定移除该角色的设计图吗？', '提示', { type: 'warning' })
    await updateCharacter(store.currentProjectId, char.id, { image_url: '' })
    char.image_url = ''
    ElMessage.success('图片已移除')
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

// AI 生成
const handleGenerateImage = async (char) => {
  if (!store.genOptions.imageProviderId) {
    return ElMessage.warning('请先在顶部选择生图模型')
  }
  
  try {
    const res = await generateCharacterViews({
      character_id: char.id,
      project_id: store.currentProjectId,
      character_description: char.description || char.name, 
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    
    if (res.success && res.status === 'queued') {
      ElNotification({
        title: '任务已提交',
        message: `正在为 ${char.name} 生成设计图，请留意后台任务队列`,
        type: 'success',
      })
    }
  } catch (e) {
    console.error(e)
  }
}

// 从设定自动生成角色列表
const handleAutoGenerateList = async () => {
  if (!store.currentProject?.visual_consistency_prompt) {
    return ElMessage.warning('请先在项目设置中填写“人物设定”或“项目基础信息”')
  }
  if (!store.genOptions.textProviderId) {
    return ElMessage.warning('请先选择文本生成模型')
  }

  generatingList.value = true
  loadingStore.start('正在分析剧本设定', 'AI 正在识别角色并生成列表...')

  try {
    const res = await generateCharacterList({
      visual_consistency_prompt: store.currentProject.visual_consistency_prompt,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })

    if (res.success && res.characters) {
      const existingNames = new Set(store.characterList.map(c => c.name.trim()))
      let addedCount = 0
      
      for (const char of res.characters) {
        if (!char.name || existingNames.has(char.name.trim())) continue
        
        const newChar = await createCharacter(store.currentProjectId, char)
        store.characterList.push(newChar)
        addedCount++
      }
      
      if (addedCount > 0) {
        ElMessage.success(`成功识别并添加了 ${addedCount} 个新角色`)
      } else {
        ElMessage.info('未发现新角色或角色已存在')
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    generatingList.value = false
    loadingStore.stop()
  }
}
</script>

<style scoped>
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

/* 使得 textarea 自适应高度且不丑 */
:deep(.el-textarea__inner) {
  height: 100% !important;
  resize: none;
}
</style>