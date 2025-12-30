<template>
  <div class="flex flex-col h-full w-full bg-gray-50 overflow-hidden">
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex justify-between items-center shrink-0 shadow-sm z-20">
      <div class="flex items-center gap-6">
        <div class="flex items-center gap-2">
          <el-icon class="text-gray-500"><SetUp /></el-icon>
          <span class="text-sm font-bold text-gray-700">AI 模型配置</span>
        </div>
        <div class="w-px h-5 bg-gray-200"></div>
        <div class="flex flex-col">
          <span class="text-[10px] text-gray-400 mb-0.5">剧本分析 / 拆解</span>
          <ModelSelector type="text" size="small" class="w-56" v-model:provider="store.genOptions.textProviderId" v-model:model="store.genOptions.textModelName" />
        </div>
        <div class="w-px h-5 bg-gray-200"></div>
        <div class="flex flex-col">
          <span class="text-[10px] text-gray-400 mb-0.5">角色形象生成</span>
          <ModelSelector type="image" size="small" class="w-56" v-model:provider="store.genOptions.imageProviderId" v-model:model="store.genOptions.imageModelName" />
        </div>
      </div>
      <div>
         <el-button type="primary" plain size="default" @click="$emit('next')">
            下一步: 细化分镜 <el-icon class="ml-1"><ArrowRight /></el-icon>
         </el-button>
      </div>
    </div>

    <div class="flex flex-1 min-h-0 w-full">
      
      <div class="w-1/3 border-r border-gray-200 flex flex-col bg-white shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-10">
        <div class="p-4 border-b border-gray-200 bg-white flex justify-between items-center z-10">
          <span class="text-gray-800 text-lg font-bold flex items-center gap-2">
            <el-icon><Document /></el-icon> 原始剧本
          </span>
          <el-button type="primary" :loading="analyzing" @click="handleAnalyzeScript" :disabled="!scriptContent.trim()" size="default">
            <el-icon class="mr-1"><MagicStick /></el-icon>
            {{ analyzing ? 'AI 分析中...' : '一键拆解分镜' }}
          </el-button>
        </div>
        <div class="flex-1 relative bg-gray-50/50">
          <el-input
            v-model="scriptContent"
            type="textarea"
            :rows=18
            class="h-full w-full absolute inset-0 script-input"
            resize="none"
            placeholder="在此处粘贴你的电影剧本... (支持 Markdown 格式)"
            @blur="handleSaveScript"
          />
        </div>
      </div>

      <div class="w-2/3 flex flex-col bg-gray-50 h-full overflow-hidden">
        
        <div class="flex-none h-[48%] border-b border-gray-200 flex flex-col bg-gray-50">
          <div class="px-4 py-2 border-b border-gray-200 bg-white flex justify-between items-center shadow-sm z-10">
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-2 text-sm font-bold text-gray-700">
                 <span class="w-1 h-4 bg-blue-500 rounded-full"></span>
                 角色列表 ({{ store.characterList.length }})
              </div>
              
              <div class="flex items-center gap-2 pl-4 border-l border-gray-200 h-6">
                 <el-checkbox 
                   v-model="isAllCharsSelected" 
                   :indeterminate="isCharIndeterminate" 
                   @change="handleSelectAllChars"
                 >
                   全选
                 </el-checkbox>
                 
                 <el-popconfirm 
                   :title="`确定删除选中的 ${selectedCharIds.length} 个角色吗？`" 
                   @confirm="handleBatchDeleteCharacters"
                   :disabled="selectedCharIds.length === 0"
                 >
                    <template #reference>
                      <el-button type="danger" link :disabled="selectedCharIds.length === 0">删除选中</el-button>
                    </template>
                 </el-popconfirm>

                 <el-popconfirm title="确定清空所有角色吗？此操作不可恢复。" @confirm="handleClearAllCharacters">
                    <template #reference>
                       <el-button type="danger" link :disabled="store.characterList.length === 0">清空全部</el-button>
                    </template>
                 </el-popconfirm>
              </div>
            </div>
            <el-button size="small" :icon="Plus" @click="handleAddCharacter">手动添加</el-button>
          </div>

          <div class="flex-1 overflow-y-auto p-4 custom-scrollbar bg-gray-100/50">
            <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              <div 
                v-for="char in store.characterList" 
                :key="char.id" 
                class="bg-white rounded-lg border transition-all group overflow-hidden flex flex-col relative cursor-pointer hover:shadow-md"
                :class="selectedCharIds.includes(char.id) ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-200'"
                @click="toggleCharSelection(char.id)"
              >
                 <div class="absolute top-2 left-2 z-20" @click.stop>
                   <el-checkbox :model-value="selectedCharIds.includes(char.id)" @change="toggleCharSelection(char.id)" />
                 </div>

                 <div class="h-32 bg-gray-100 relative shrink-0">
                   <UnifiedImageCard
                      :src="char.image_url"
                      width="100%"
                      height="100%"
                      fit="cover"
                      placeholder="角色图"
                      custom-class="!border-0 !rounded-none"
                      :enable-generate="true"
                      :enable-upload="true"
                      :enable-delete="true"
                      @generate="handleGenerateCharImage(char)"
                      @upload="(file) => handleCharUpload(char, file)"
                      @delete="handleCharImageDelete(char)"
                   />
                 </div>
                 
                 <div class="p-2 flex flex-col gap-2 flex-1 min-h-0" @click.stop>
                   <input 
                     v-model="char.name" 
                     class="font-bold text-gray-800 border-b border-transparent focus:border-blue-500 outline-none px-1 py-0.5 bg-transparent w-full text-sm"
                     placeholder="角色名"
                     @change="handleUpdateCharacter(char)"
                   />
                   <textarea 
                     v-model="char.description" 
                     class="text-xs text-gray-500 w-full bg-gray-50 p-1.5 rounded border-transparent focus:border-blue-300 focus:bg-white outline-none resize-none flex-1 leading-relaxed"
                     placeholder="外貌/性格描述..."
                     @change="handleUpdateCharacter(char)"
                   ></textarea>
                 </div>
              </div>

              <div 
                class="border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center text-gray-400 hover:text-blue-500 hover:border-blue-400 hover:bg-blue-50 transition-all cursor-pointer min-h-[220px]" 
                @click="handleAddCharacter"
              >
                <el-icon :size="24"><Plus /></el-icon>
                <span class="text-xs mt-2 font-medium">新建角色</span>
              </div>
            </div>
          </div>
        </div>

        <div class="flex-1 flex flex-col overflow-hidden bg-white">
          <div class="px-4 py-2 border-b border-gray-200 bg-white flex justify-between items-center shadow-sm z-10">
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-2 text-sm font-bold text-gray-700">
                <span class="w-1 h-4 bg-green-500 rounded-full"></span>
                <span>分镜列表 ({{ store.shotList.length }})</span>
              </div>

              <div class="flex items-center gap-2 pl-4 border-l border-gray-200 h-6">
                 <el-checkbox 
                   v-model="isAllShotsSelected" 
                   :indeterminate="isShotIndeterminate" 
                   @change="handleSelectAllShots"
                 >
                   全选
                 </el-checkbox>

                 <el-popconfirm 
                   :title="`确定删除选中的 ${selectedShotIds.length} 个分镜吗？`" 
                   @confirm="handleBatchDeleteShots"
                   :disabled="selectedShotIds.length === 0"
                 >
                    <template #reference>
                       <el-button type="danger" link :disabled="selectedShotIds.length === 0">删除选中</el-button>
                    </template>
                 </el-popconfirm>

                 <el-popconfirm title="确定清空所有分镜吗？" @confirm="handleClearAllShots">
                    <template #reference>
                       <el-button type="danger" link :disabled="store.shotList.length === 0">清空全部</el-button>
                    </template>
                 </el-popconfirm>
              </div>
            </div>
            
            <div class="flex gap-2">
               <el-button link type="primary" size="small" :icon="Refresh" @click="refreshShots">刷新</el-button>
               <el-button size="small" :icon="Plus" @click="handleAddShot">添加分镜</el-button>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar bg-gray-50">
            <div 
              v-for="(shot, index) in store.shotList" 
              :key="shot.id" 
              class="bg-white p-3 rounded-lg border flex gap-3 shadow-sm hover:border-blue-400 transition-all group items-start relative cursor-pointer"
              :class="selectedShotIds.includes(shot.id) ? 'border-blue-400 bg-blue-50/20' : 'border-gray-200'"
              @click="toggleShotSelection(shot.id)"
            >
              <div class="pt-2" @click.stop>
                <el-checkbox :model-value="selectedShotIds.includes(shot.id)" @change="toggleShotSelection(shot.id)" />
              </div>

              <div class="flex-none w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-500 text-sm mt-1">
                {{ shot.shot_number || index + 1 }}
              </div>

              <div class="flex-1 space-y-2" @click.stop>
                <div class="flex items-start gap-2">
                   <span class="text-xs font-bold text-gray-400 bg-gray-100 px-1.5 rounded pt-0.5 whitespace-nowrap">场 {{ shot.scene }}</span>
                   <el-input 
                     v-model="shot.visual_description" 
                     type="textarea" 
                     :autosize="{ minRows: 1, maxRows: 3 }"
                     class="w-full !text-base font-medium"
                     placeholder="描述分镜画面..." 
                     @change="handleUpdateShot(shot)"
                   />
                </div>
                
                <div class="flex flex-wrap gap-3 items-center">
                   <!-- <el-select v-model="shot.shot_size" size="small" class="w-28" placeholder="景别" @change="handleUpdateShot(shot)">
                      <el-option value="Extremely Long Shot" label="大远景" />
                      <el-option value="Long Shot" label="远景" />
                      <el-option value="Full Shot" label="全景" />
                      <el-option value="Medium Shot" label="中景" />
                      <el-option value="Close Up" label="特写" />
                      <el-option value="Extreme Close Up" label="大特写" />
                   </el-select> -->

                   <div class="flex items-center gap-1 bg-gray-50 border border-gray-200 rounded px-2 h-6">
                      <el-icon class="text-gray-400 text-xs"><Timer /></el-icon>
                      <input v-model="shot.duration" type="number" class="bg-transparent text-xs text-gray-700 w-8 outline-none text-center" placeholder="s" @change="handleUpdateShot(shot)" />
                      <span class="text-xs text-gray-400">s</span>
                   </div>

                   <el-select 
                     v-model="shot.characters"
                     multiple
                     collapse-tags-tooltip
                     placeholder="选择角色"
                     size="small"
                     class="w-64"
                     @change="handleUpdateShot(shot)"
                   >
                     <el-option 
                       v-for="char in store.characterList" 
                       :key="char.id" 
                       :label="char.name" 
                       :value="char.id" 
                     />
                   </el-select>
                </div>
              </div>

              <el-button 
                type="danger" 
                link 
                :icon="Close" 
                class="self-start opacity-0 group-hover:opacity-100 transition-opacity"
                @click.stop="handleRemoveShot(shot)" 
              />
            </div>

            <el-button 
              @click="handleAddShot" 
              class="w-full py-3 border border-dashed border-gray-300 text-gray-400 hover:text-blue-600 hover:border-blue-400 hover:bg-blue-50 rounded-lg transition-all"
              icon="Plus"
            >
              添加分镜
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'
import ModelSelector from '@/components/ModelSelector.vue'

// API Imports
import { 
  getScript, saveScript, 
  createCharacter, updateCharacter, deleteCharacter, batchDeleteCharacters,
  getShots, createShot, updateShot, deleteShot, batchDeleteShots
} from '@/api/project'
import { 
  analyzeScript, 
  generateCharacterViews, 
  uploadCharacterImage 
} from '@/api/generation'

import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Plus, Close, MagicStick, Timer, ArrowRight, Document, Refresh, SetUp } from '@element-plus/icons-vue'

const props = defineProps(['projectId'])
const emit = defineEmits(['next', 'prev'])

const store = useProjectStore()
const loadingStore = useLoadingStore()

// State
const scriptContent = ref('')
const analyzing = ref(false)
const scriptSections = ref([]) 
const selectedCharIds = ref([])
const selectedShotIds = ref([])

// --- Initialization ---

const initData = async (id) => {
  if (!id) return
  if (store.currentProjectId !== id) await store.initProject(id)
  await Promise.all([
    fetchScript(),
    store.characterList.length === 0 ? store.fetchCharacters() : Promise.resolve(),
    store.shotList.length === 0 ? store.fetchShots() : Promise.resolve()
  ])
  selectedCharIds.value = []
  selectedShotIds.value = []
}

onMounted(() => {
  const targetId = props.projectId || store.currentProjectId
  if (targetId) initData(targetId)
})

watch(() => props.projectId, (newId) => {
  if (newId) initData(newId)
})

watch(() => store.currentProjectId, (newId) => {
  if (newId && !scriptContent.value) initData(newId)
})

// --- Computed Properties for Selection ---

const isAllCharsSelected = computed({
  get: () => store.characterList.length > 0 && selectedCharIds.value.length === store.characterList.length,
  set: (val) => handleSelectAllChars(val)
})
const isCharIndeterminate = computed(() => selectedCharIds.value.length > 0 && selectedCharIds.value.length < store.characterList.length)

const isAllShotsSelected = computed({
  get: () => store.shotList.length > 0 && selectedShotIds.value.length === store.shotList.length,
  set: (val) => handleSelectAllShots(val)
})
const isShotIndeterminate = computed(() => selectedShotIds.value.length > 0 && selectedShotIds.value.length < store.shotList.length)

// --- Script Logic ---
const fetchScript = async () => {
  if (!store.currentProjectId) return
  try {
    const res = await getScript(store.currentProjectId)
    scriptSections.value = res || []
    scriptContent.value = scriptSections.value.map(s => s.content).join('\n\n')
  } catch (e) { console.error(e) }
}

const handleSaveScript = async () => {
  if (!store.currentProjectId) return
  const newSections = scriptSections.value.length > 0 
    ? [{ ...scriptSections.value[0], content: scriptContent.value }]
    : [{ content: scriptContent.value }]
  try {
    await saveScript(store.currentProjectId, newSections)
    scriptSections.value = newSections
  } catch (e) { console.error(e) }
}

const handleAnalyzeScript = async () => {
  if (!scriptContent.value.trim()) return ElMessage.warning('剧本内容为空')
  if (!store.genOptions.textProviderId) return ElMessage.warning('请先在顶部选择剧本分析模型')
  
  analyzing.value = true
  loadingStore.start('正在拆解剧本', 'AI 正在分析场景、角色与分镜...')
  
  try {
    await handleSaveScript()
    
    // 1. 调用 AI 分析
    const res = await analyzeScript({
      content: scriptContent.value,
      project_id: store.currentProjectId,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })

    // [BUG FIX 1] 刷新角色列表，因为 analyzeScript 可能在后台创建了新角色
    await store.fetchCharacters()

    if (res.shots && res.shots.length > 0) {
      let count = 0
      for (const shotData of res.shots) {
        
        // [BUG FIX 2] 提取角色 ID
        const charIds = shotData.characters && Array.isArray(shotData.characters) 
            ? shotData.characters.map(c => c.id) 
            : []

        await createShot(store.currentProjectId, {
          movie_id: store.currentProjectId,
          scene: shotData.scene || '1',
          shot_number: shotData.shot_number || (count + 1).toString(),
          visual_description: shotData.visual_description || shotData.content,
          dialogue: shotData.dialogue || '',
          shot_size: shotData.shot_size || 'Medium Shot',
          duration: shotData.duration || 3,
          characters: charIds 
        })
        count++
      }
      
      await store.fetchShots()
      ElNotification.success({ title: '拆解完成', message: `成功生成 ${count} 个分镜` })
    } else {
      ElMessage.warning('AI 未能识别出有效内容')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('分析失败')
  } finally {
    analyzing.value = false
    loadingStore.stop()
  }
}

// --- Character Logic (CRUD + Batch) ---

const handleSelectAllChars = (val) => {
  selectedCharIds.value = val ? store.characterList.map(c => c.id) : []
}

const toggleCharSelection = (id) => {
  const idx = selectedCharIds.value.indexOf(id)
  if (idx > -1) selectedCharIds.value.splice(idx, 1)
  else selectedCharIds.value.push(id)
}

const handleBatchDeleteCharacters = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedCharIds.value.length} 个角色吗？`, '批量删除')
    await batchDeleteCharacters(store.currentProjectId, selectedCharIds.value)
    store.characterList = store.characterList.filter(c => !selectedCharIds.value.includes(c.id))
    selectedCharIds.value = []
    ElMessage.success('批量删除成功')
  } catch (e) { if(e !== 'cancel') console.error(e) }
}

const handleClearAllCharacters = async () => {
  try {
    const allIds = store.characterList.map(c => c.id)
    await batchDeleteCharacters(store.currentProjectId, allIds)
    store.characterList = []
    selectedCharIds.value = []
    ElMessage.success('已清空所有角色')
  } catch (e) { console.error(e) }
}

const handleAddCharacter = async () => {
  try {
    const newChar = await createCharacter(store.currentProjectId, { name: '新角色', description: '' })
    store.characterList.push(newChar)
  } catch (e) { console.error(e) }
}
const handleUpdateCharacter = async (char) => {
  try { await updateCharacter(store.currentProjectId, char.id, { name: char.name, description: char.description }) } catch (e) {}
}
const handleGenerateCharImage = async (char) => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请选择生图模型')
  if (!char.description && !char.name) return ElMessage.warning('请填写描述')
  try {
    const res = await generateCharacterViews({
      character_id: char.id,
      project_id: store.currentProjectId,
      character_description: char.description || char.name,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    if(res.success) ElMessage.success('任务已提交')
  } catch(e) {}
}
const handleCharUpload = async (char, file) => {
  loadingStore.start('上传中', '正在上传图片...')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('character_id', char.id)
  try {
    const res = await uploadCharacterImage(fd)
    if (res.success) {
      await updateCharacter(store.currentProjectId, char.id, { image_url: res.url })
      char.image_url = res.url
      ElMessage.success('上传成功')
    }
  } catch(e) {} finally { loadingStore.stop() }
}
const handleCharImageDelete = async (char) => {
  await updateCharacter(store.currentProjectId, char.id, { image_url: '' })
  char.image_url = ''
}

// --- Shot Logic (CRUD + Batch) ---

const handleSelectAllShots = (val) => {
  selectedShotIds.value = val ? store.shotList.map(s => s.id) : []
}

const toggleShotSelection = (id) => {
  const idx = selectedShotIds.value.indexOf(id)
  if (idx > -1) selectedShotIds.value.splice(idx, 1)
  else selectedShotIds.value.push(id)
}

const handleBatchDeleteShots = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedShotIds.value.length} 个分镜吗？`, '批量删除')
    await batchDeleteShots(store.currentProjectId, selectedShotIds.value)
    store.shotList = store.shotList.filter(s => !selectedShotIds.value.includes(s.id))
    selectedShotIds.value = []
    ElMessage.success('批量删除成功')
  } catch (e) { if(e !== 'cancel') console.error(e) }
}

const handleClearAllShots = async () => {
  try {
    const allIds = store.shotList.map(s => s.id)
    await batchDeleteShots(store.currentProjectId, allIds)
    store.shotList = []
    selectedShotIds.value = []
    ElMessage.success('已清空所有分镜')
  } catch (e) { console.error(e) }
}

const refreshShots = () => store.fetchShots()
const handleAddShot = async () => {
  let scene = '1'
  if (store.shotList.length > 0) scene = store.shotList[store.shotList.length - 1].scene
  try {
    const newShot = await createShot(store.currentProjectId, {
      movie_id: store.currentProjectId,
      scene: scene,
      visual_description: '',
      shot_size: 'Medium Shot',
      duration: 3
    })
    store.shotList.push(newShot)
  } catch(e) {}
}
const handleUpdateShot = async (shot) => {
  try { await updateShot(store.currentProjectId, shot.id, { 
    visual_description: shot.visual_description, 
    shot_size: shot.shot_size, 
    duration: shot.duration,
    characters: shot.characters // 这里确保将角色列表提交到后端
  }) } catch(e) {}
}
const handleRemoveShot = async (shot) => {
  try {
    await deleteShot(store.currentProjectId, shot.id)
    store.shotList = store.shotList.filter(s => s.id !== shot.id)
    const idx = selectedShotIds.value.indexOf(shot.id)
    if(idx > -1) selectedShotIds.value.splice(idx, 1)
  } catch(e) {}
}

// Helpers
const getCharName = (idOrObj) => {
  const id = typeof idOrObj === 'object' ? idOrObj.id : idOrObj
  const char = store.characterList.find(c => c.id === id)
  return char ? char.name : '?'
}
const getCharImg = (idOrObj) => {
  const id = typeof idOrObj === 'object' ? idOrObj.id : idOrObj
  const char = store.characterList.find(c => c.id === id)
  return char ? char.image_url : ''
}
</script>

<style scoped>
.script-input :deep(.el-textarea__inner) {
  border: none;
  border-radius: 0;
  padding: 1.5rem;
  font-size: 1rem;
  line-height: 1.75;
  color: #374151;
  background-color: transparent;
  box-shadow: none;
}
.script-input :deep(.el-textarea__inner:focus) {
  background-color: white;
}
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #d1d5db;
  border-radius: 3px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #9ca3af;
}
</style>