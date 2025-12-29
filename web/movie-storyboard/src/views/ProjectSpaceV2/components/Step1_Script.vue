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
          <ModelSelector 
            type="text" 
            size="small"
            class="w-56"
            v-model:provider="store.genOptions.textProviderId" 
            v-model:model="store.genOptions.textModelName" 
          />
        </div>

        <div class="w-px h-5 bg-gray-200"></div>

        <div class="flex flex-col">
          <span class="text-[10px] text-gray-400 mb-0.5">角色形象生成</span>
          <ModelSelector 
            type="image" 
            size="small" 
            class="w-56"
            v-model:provider="store.genOptions.imageProviderId" 
            v-model:model="store.genOptions.imageModelName" 
          />
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
          <el-button 
            type="primary" 
            :loading="analyzing" 
            @click="handleAnalyzeScript"
            :disabled="!scriptContent.trim()"
            size="default"
          >
            <el-icon class="mr-1"><MagicStick /></el-icon>
            {{ analyzing ? 'AI 分析中...' : '一键拆解分镜' }}
          </el-button>
        </div>
        
        <div class="flex-1 relative bg-gray-50/50">
          <el-input
            v-model="scriptContent"
            type="textarea"
            :rows=24
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
            <div class="flex items-center gap-2 text-sm font-bold text-gray-700">
               <span class="w-1 h-4 bg-blue-500 rounded-full"></span>
               角色列表 ({{ store.characterList.length }})
               <span class="text-xs text-gray-400 font-normal ml-2">AI 将自动提取角色，也可手动添加</span>
            </div>
            <el-button size="small" :icon="Plus" @click="handleAddCharacter">手动添加</el-button>
          </div>

          <div class="flex-1 overflow-y-auto p-4 custom-scrollbar bg-gray-100/50">
            <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              <div 
                v-for="char in store.characterList" 
                :key="char.id" 
                class="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all group overflow-hidden flex flex-col"
              >
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
                   <div class="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                      <el-button type="danger" circle size="small" :icon="Close" @click="handleDeleteCharacter(char)" />
                   </div>
                 </div>
                 
                 <div class="p-2 flex flex-col gap-2 flex-1 min-h-0">
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
            <div class="flex items-center gap-2 text-sm font-bold text-gray-700">
              <span class="w-1 h-4 bg-green-500 rounded-full"></span>
              <span>分镜列表 ({{ store.shotList.length }})</span>
              <span class="text-xs text-gray-400 font-normal ml-2">分析结果将展示在此处</span>
            </div>
            <el-button link type="primary" size="small" :icon="Refresh" @click="refreshShots">刷新</el-button>
          </div>

          <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar bg-gray-50">
            <div 
              v-for="(shot, index) in store.shotList" 
              :key="shot.id" 
              class="bg-white p-3 rounded-lg border border-gray-200 flex gap-4 shadow-sm hover:border-blue-400 transition-all group items-start"
            >
              <div class="flex-none w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-500 text-sm mt-1">
                {{ shot.shot_number || index + 1 }}
              </div>

              <div class="flex-1 space-y-2">
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
                   <el-select 
                     v-model="shot.shot_size" 
                     size="small" 
                     class="w-28" 
                     placeholder="景别" 
                     @change="handleUpdateShot(shot)"
                   >
                      <el-option value="Extremely Long Shot" label="大远景" />
                      <el-option value="Long Shot" label="远景" />
                      <el-option value="Full Shot" label="全景" />
                      <el-option value="Medium Shot" label="中景" />
                      <el-option value="Close Up" label="特写" />
                      <el-option value="Extreme Close Up" label="大特写" />
                   </el-select>

                   <div class="flex items-center gap-1 bg-gray-50 border border-gray-200 rounded px-2 h-6">
                      <el-icon class="text-gray-400 text-xs"><Timer /></el-icon>
                      <input 
                        v-model="shot.duration" 
                        type="number" 
                        class="bg-transparent text-xs text-gray-700 w-8 outline-none text-center" 
                        placeholder="s" 
                        @change="handleUpdateShot(shot)"
                      />
                      <span class="text-xs text-gray-400">s</span>
                   </div>

                   <div class="flex -space-x-1 overflow-hidden" v-if="shot.characters && shot.characters.length">
                      <div 
                        v-for="cid in shot.characters" 
                        :key="cid" 
                        class="w-6 h-6 rounded-full border border-white bg-gray-200 flex items-center justify-center text-[8px] overflow-hidden"
                        :title="getCharName(cid)"
                      >
                         <img v-if="getCharImg(cid)" :src="getCharImg(cid)" class="w-full h-full object-cover" />
                         <span v-else>{{ getCharName(cid).charAt(0) }}</span>
                      </div>
                   </div>
                </div>
              </div>

              <el-button 
                type="danger" 
                link 
                :icon="Close" 
                class="self-start opacity-0 group-hover:opacity-100 transition-opacity"
                @click="handleRemoveShot(shot)" 
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
import { ref, onMounted, watch } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'
import ModelSelector from '@/components/ModelSelector.vue'

// API Imports
import { 
  getScript, saveScript, 
  createCharacter, updateCharacter, deleteCharacter,
  getShots, createShot, updateShot, deleteShot 
} from '@/api/project'
import { 
  analyzeScript, 
  generateCharacterViews, 
  uploadCharacterImage 
} from '@/api/generation'

import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Plus, Close, MagicStick, Timer, ArrowRight, Document, Refresh, SetUp } from '@element-plus/icons-vue'

const props = defineProps(['projectId']) // 确保父组件传了 :project-id
const emit = defineEmits(['next', 'prev'])

const store = useProjectStore()
const loadingStore = useLoadingStore()

// State
const scriptContent = ref('')
const analyzing = ref(false)
const scriptSections = ref([]) 

// --- Initialization Logic (Fixing null ID) ---

const initData = async (id) => {
  if (!id) return
  
  // 确保 store 中的 ID 已更新，防止 API 调用错乱
  if (store.currentProjectId !== id) {
     await store.initProject(id)
  }

  // 并行加载本页面所需数据
  await Promise.all([
    fetchScript(),
    // 角色和分镜数据如果 store.initProject 已经加载过，这里就不需要重复全量加载
    // 但为了保险起见，或者如果是从别的页面切过来，可以检查列表是否为空
    store.characterList.length === 0 ? store.fetchCharacters() : Promise.resolve(),
    store.shotList.length === 0 ? store.fetchShots() : Promise.resolve()
  ])
}

// 1. 组件挂载时检查
onMounted(() => {
  const targetId = props.projectId || store.currentProjectId
  if (targetId) {
    initData(targetId)
  }
})

// 2. 监听 Props 变化 (解决父组件异步获取 ID 的情况)
watch(() => props.projectId, (newId) => {
  if (newId) {
    initData(newId)
  }
})

// 3. 监听 Store 变化 (解决 Store 延迟初始化的情况)
watch(() => store.currentProjectId, (newId) => {
  if (newId && !scriptContent.value) { // 只有当内容为空时才尝试加载，避免覆盖
    initData(newId)
  }
})

// --- Script Logic ---
const fetchScript = async () => {
  if (!store.currentProjectId) return
  try {
    const res = await getScript(store.currentProjectId)
    scriptSections.value = res || []
    scriptContent.value = scriptSections.value.map(s => s.content).join('\n\n')
  } catch (e) {
    console.error(e)
  }
}

const handleSaveScript = async () => {
  if (!store.currentProjectId) return
  const newSections = scriptSections.value.length > 0 
    ? [{ ...scriptSections.value[0], content: scriptContent.value }]
    : [{ content: scriptContent.value }]
    
  try {
    await saveScript(store.currentProjectId, newSections)
    scriptSections.value = newSections
  } catch (e) {
    console.error('Script save failed', e)
  }
}

const handleAnalyzeScript = async () => {
  if (!scriptContent.value.trim()) return ElMessage.warning('剧本内容为空')
  if (!store.genOptions.textProviderId) return ElMessage.warning('请先在顶部选择剧本分析模型')
  
  analyzing.value = true
  loadingStore.start('正在拆解剧本', 'AI 正在分析场景、角色与分镜...')
  
  try {
    await handleSaveScript()
    const res = await analyzeScript({
      content: scriptContent.value,
      project_id: store.currentProjectId,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })

    if (res.shots && res.shots.length > 0) {
      let count = 0
      for (const shotData of res.shots) {
        await createShot(store.currentProjectId, {
          movie_id: store.currentProjectId,
          scene: shotData.scene || '1',
          shot_number: shotData.shot_number || (count + 1).toString(),
          visual_description: shotData.visual_description || shotData.content,
          dialogue: shotData.dialogue || '',
          shot_size: shotData.shot_size || 'Medium Shot',
          duration: shotData.duration || 3
        })
        count++
      }
      
      await store.fetchShots()
      ElNotification.success({ title: '拆解完成', message: `成功生成 ${count} 个分镜` })
    } else {
      ElMessage.warning('AI 未能识别出有效内容，请检查剧本格式')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('分析失败: ' + (e.message || '未知错误'))
  } finally {
    analyzing.value = false
    loadingStore.stop()
  }
}

// --- Character Logic ---
const handleAddCharacter = async () => {
  try {
    const newChar = await createCharacter(store.currentProjectId, { name: '新角色', description: '' })
    store.characterList.push(newChar)
  } catch (e) { console.error(e) }
}

const handleUpdateCharacter = async (char) => {
  try {
    await updateCharacter(store.currentProjectId, char.id, { name: char.name, description: char.description })
  } catch (e) { console.error(e) }
}

const handleDeleteCharacter = async (char) => {
  try {
    await ElMessageBox.confirm(`删除角色 ${char.name}?`)
    await deleteCharacter(store.currentProjectId, char.id)
    store.characterList = store.characterList.filter(c => c.id !== char.id)
  } catch (e) {}
}

const handleGenerateCharImage = async (char) => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请先在顶部选择生图模型')
  if (!char.description && !char.name) return ElMessage.warning('请填写角色描述')
  
  try {
    const res = await generateCharacterViews({
      character_id: char.id,
      project_id: store.currentProjectId,
      character_description: char.description || char.name,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    if(res.success) ElMessage.success('任务已提交，请稍候')
  } catch(e) { console.error(e) }
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
  } catch(e) { console.error(e) } finally { loadingStore.stop() }
}

const handleCharImageDelete = async (char) => {
  await updateCharacter(store.currentProjectId, char.id, { image_url: '' })
  char.image_url = ''
}

// --- Shot Logic ---
const refreshShots = () => store.fetchShots()

const handleAddShot = async () => {
  let scene = '1'
  if (store.shotList.length > 0) {
    scene = store.shotList[store.shotList.length - 1].scene
  }
  try {
    const newShot = await createShot(store.currentProjectId, {
      movie_id: store.currentProjectId,
      scene: scene,
      visual_description: '',
      shot_size: 'Medium Shot',
      duration: 3
    })
    store.shotList.push(newShot)
  } catch(e) { console.error(e) }
}

const handleUpdateShot = async (shot) => {
  try {
    await updateShot(store.currentProjectId, shot.id, {
      visual_description: shot.visual_description,
      shot_size: shot.shot_size,
      duration: shot.duration
    })
  } catch(e) { console.error(e) }
}

const handleRemoveShot = async (shot) => {
  try {
    await deleteShot(store.currentProjectId, shot.id)
    store.shotList = store.shotList.filter(s => s.id !== shot.id)
  } catch(e) { console.error(e) }
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