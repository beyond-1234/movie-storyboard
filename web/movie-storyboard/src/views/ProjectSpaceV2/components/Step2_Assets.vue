<template>
  <div class="h-full flex flex-col bg-gray-50">
    <div class="h-14 border-b border-gray-200 flex items-center px-6 justify-between bg-white shadow-sm z-10 shrink-0">
      <div class="text-sm text-gray-500 font-medium flex items-center gap-4">
        <div>
          <span class="bg-blue-50 text-blue-600 px-2 py-1 rounded text-xs mr-2 font-bold">ASSETS</span>
          <span>共 {{ store.shotList.length }} 个分镜待处理</span>
        </div>
        
        <div class="flex items-center gap-2 text-xs bg-gray-100 px-3 py-1 rounded-full">
           <span class="text-gray-400">当前模型:</span>
           <span class="font-bold text-gray-700">{{ store.genOptions.imageModelName || '未选择' }}</span>
        </div>
      </div>
      
      <div class="space-x-3">
        <el-button @click="$emit('prev')" class="text-gray-500 hover:text-gray-800 text-sm px-3 font-medium">上一步</el-button>
        <el-button type="primary" plain @click="refreshData" :icon="Refresh">刷新数据</el-button>
        <el-button @click="$emit('next')" class="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-1.5 rounded shadow-sm transition-colors">下一步 (剪辑)</el-button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
      <div v-for="(shot, index) in store.shotList" :key="shot.id" class="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow">
        
        <div class="flex items-center justify-between mb-6 border-b border-gray-100 pb-4">
          <div class="flex items-center gap-4">
             <div class="flex flex-col items-center justify-center bg-gray-100 w-12 h-12 rounded-lg">
               <span class="text-xs text-gray-400">SCENE</span>
               <span class="text-xl font-bold text-gray-700">{{ shot.scene }}</span>
             </div>
             <div>
                <p class="text-gray-800 font-bold text-lg line-clamp-1" :title="shot.visual_description">{{ shot.visual_description || '暂无画面描述' }}</p>
                <div class="flex gap-2 mt-1">
                   <span class="text-xs text-gray-400">镜号: {{ shot.shot_number }}</span>
                   <span class="text-xs text-blue-500" v-if="shot.dialogue">“{{ shot.dialogue }}”</span>
                </div>
             </div>
          </div>
          <span class="text-xs bg-gray-50 text-gray-500 px-3 py-1 rounded border border-gray-200 font-medium">
            {{ shot.shot_size || 'Unknown' }} / {{ shot.duration }}s
          </span>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div class="space-y-3 group flex flex-col">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-blue-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span> Step 2.1: 场景底图
              </span>
              <el-button link type="primary" size="small" @click="handleGenScenePrompt(shot)" :loading="shot._loadingPrompt">
                 {{ shot.scene_prompt ? '重成Prompt' : '生成Prompt' }}
              </el-button>
            </div>
            
            <el-input 
              type="textarea" 
              class="w-full text-sm" 
              :rows="3"
              resize="none"
              v-model="shot.scene_prompt" 
              placeholder="场景提示词 (Scene Prompt)..."
            />
            
            <div class="flex-1 min-h-[220px]">
               <UnifiedImageCard
                 :src="shot.scene_image"
                 width="100%"
                 height="100%"
                 fit="cover"
                 placeholder="场景底图"
                 :enable-generate="true"
                 :enable-upload="true"
                 :enable-delete="!!shot.scene_image"
                 @generate="handleGenSceneImage(shot)"
                 @upload="(file) => handleSceneUpload(shot, file)"
                 @delete="handleDeleteSceneImage(shot)"
               >
                 <template #info>Scene Base</template>
               </UnifiedImageCard>
            </div>
          </div>

          <div class="space-y-3 group flex flex-col">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-purple-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-purple-500"></span> Step 2.2: 动作九宫格
              </span>
              <el-button 
                link type="primary" size="small" 
                @click="handleGenGridPrompt(shot)"
              >
                 生成Prompt
              </el-button>
            </div>

            <el-input 
              type="textarea" 
              class="w-full text-sm" 
              :rows="3"
              resize="none"
              v-model="shot.grid_prompt" 
              placeholder="九宫格提示词 (9-Grid Prompt)..."
            />

            <div class="flex-1 min-h-[220px]">
               <UnifiedImageCard
                 :src="shot.grid_image"
                 width="100%"
                 height="100%"
                 fit="contain"
                 placeholder="9宫格动作预览"
                 :enable-generate="true"
                 :enable-upload="true"
                 :enable-delete="!!shot.grid_image"
                 @generate="handleGenGridImage(shot)"
                 @upload="(file) => handleGridUpload(shot, file)"
                 @delete="handleDeleteGridImage(shot)"
               >
                 <template #info>Action Grid</template>
               </UnifiedImageCard>
            </div>
            
            <div class="text-[10px] text-gray-400 px-1">
               <span v-if="shot.scene_image">✅ 底图已就绪</span>
               <span v-else>⚠️ 缺少底图</span>
               <span class="mx-1">|</span>
               <span>角色: {{ getShotCharNames(shot).join(', ') || '无' }}</span>
            </div>
          </div>

          <div class="space-y-3 group flex flex-col">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-green-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-green-500"></span> Step 2.3: 动态视频
              </span>
            </div>
            
             <div class="h-[74px] bg-gray-50 border border-gray-200 rounded p-2 text-xs text-gray-500 flex items-center justify-center">
                <span>视频生成将基于九宫格或底图</span>
             </div>

            <div class="flex-1 min-h-[220px] bg-gray-100 rounded-lg border border-gray-200 relative overflow-hidden flex items-center justify-center">
               <video 
                 v-if="shot.video_url" 
                 :src="shot.video_url" 
                 controls 
                 class="w-full h-full object-cover"
               ></video>
               <div v-else class="text-gray-400 text-xs flex flex-col items-center gap-2">
                 <span class="text-2xl">🎬</span>
                 <span>等待生成</span>
               </div>
               
               <div class="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-end p-2 pointer-events-none">
                  <el-button 
                    class="bg-green-600 text-white text-xs px-3 py-1.5 rounded shadow-lg pointer-events-auto hover:bg-green-700 border-none"
                    :disabled="!shot.grid_image && !shot.scene_image"
                    @click="ElMessage.info('视频生成逻辑待对接 (建议使用 Grid 或 Scene)')"
                  >
                    {{ shot.video_url ? '重新生成' : '生成视频' }}
                  </el-button>
               </div>
            </div>
          </div>

        </div>
      </div>
      
      <el-empty v-if="store.shotList.length === 0" description="暂无分镜，请先在第一步生成分镜" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/api'  // 假设有个通用 axios 封装，或直接用 fetch
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'
import { Refresh, RefreshRight, Connection } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'

// API Imports (保留部分原有，新增 Grid 相关)
import { 
  generateScenePrompt, generateSceneImage, uploadSceneImage, uploadGridImage,
  uploadBaseImage // 复用上传接口
} from '@/api/generation'
import { updateShot } from '@/api/project'

const props = defineProps(['projectId'])
const emit = defineEmits(['next', 'prev'])

const store = useProjectStore()
const loadingStore = useLoadingStore()

// --- Initialization ---

onMounted(async () => {
  await refreshData()
})

const refreshData = async () => {
  if (store.currentProjectId) {
    loadingStore.start('加载中', '正在同步数据...')
    try {
      await store.fetchShots()
      await store.fetchCharacters()
    } finally {
      loadingStore.stop()
    }
  }
}

// --- Helpers ---

const getShotCharNames = (shot) => {
  if (!shot.characters) return []
  // 处理 characters 可能是 ID 数组或对象数组的情况
  return shot.characters.map(c => {
    const id = typeof c === 'object' ? c.id : c
    const charObj = store.characterList.find(x => x.id === id)
    return charObj ? charObj.name : '未知'
  })
}

const getShotCharImages = (shot) => {
   if (!shot.characters) return []
   return shot.characters.map(c => {
    const id = typeof c === 'object' ? c.id : c
    const charObj = store.characterList.find(x => x.id === id)
    return charObj ? charObj.image_url : null
  }).filter(url => url)
}

// --- Step 2.1: Scene Logic ---

const handleGenScenePrompt = async (shot) => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请配置文本模型')
  
  shot._loadingPrompt = true
  try {
    const res = await generateScenePrompt({
      scene_id: shot.id,
      project_id: store.currentProjectId,
      scene_description: shot.scene_description || shot.visual_description,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    if (res.success && res.prompt) {
      shot.scene_prompt = res.prompt
      // 触发保存
      await updateShot(store.currentProjectId, shot.id, { scene_prompt: res.prompt })
    }
  } catch (e) {
    console.error(e)
  } finally {
    shot._loadingPrompt = false
  }
}

const handleGenSceneImage = async (shot) => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请配置生图模型')
  if (!shot.scene_prompt) return ElMessage.warning('请先生成提示词')
  
  try {
    // 调用异步接口
    const res = await request.post('/api/async/generate/scene_image', {
      scene_id: shot.id,
      project_id: store.currentProjectId,
      scene_prompt: shot.scene_prompt,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    
    if (res.success) {
      ElNotification.success({ title: '任务提交成功', message: '场景底图正在生成中...' })
    }
  } catch (e) { console.error(e) }
}

const handleSceneUpload = async (shot, file) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('scene_id', shot.id)
  loadingStore.start('上传中')
  try {
    const res = await uploadSceneImage(fd)
    if (res.success) {
      shot.scene_image = res.url
      await updateShot(store.currentProjectId, shot.id, { scene_image: res.url })
      ElMessage.success('上传成功')
    }
  } finally { loadingStore.stop() }
}

const handleDeleteSceneImage = async (shot) => {
  shot.scene_image = ''
  await updateShot(store.currentProjectId, shot.id, { scene_image: '' })
}

// --- Step 2.2: 9-Grid Logic (New) ---

const handleGenGridPrompt = async (shot) => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请配置文本模型')
  
  try {
    const res = await request.post('/api/generate/grid_prompt', {
      scene_description: shot.scene_description || shot.visual_description,
      shot_description: shot.visual_description,
      character_names: getShotCharNames(shot),
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    
    if (res.success && res.prompt) {
      shot.grid_prompt = res.prompt
      await updateShot(store.currentProjectId, shot.id, { grid_prompt: res.prompt })
      ElMessage.success('九宫格提示词已生成')
    }
  } catch(e) { console.error(e) }
}

const handleGenGridImage = async (shot) => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请配置生图模型')
  if (!shot.grid_prompt) return ElMessage.warning('请先生成提示词')
  
  try {
    // 调用异步 Grid 生成接口
    const res = await request.post('/api/async/generate/grid_image', {
      shot_id: shot.id,
      project_id: store.currentProjectId,
      grid_prompt: shot.grid_prompt,
      base_image_url: shot.scene_image, // 传入底图
      character_images: getShotCharImages(shot), // 传入角色图列表
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    
    if (res.success) {
      ElNotification.success({ title: '任务已提交', message: '正在生成九宫格...' })
    }
  } catch(e) { console.error(e) }
}

const handleGridUpload = async (shot, file) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('shot_id', shot.id)
  loadingStore.start('上传中')
  try {
    const res = await uploadGridImage(fd)
    if (res.success) {
      shot.scene_image = res.url
      await updateShot(store.currentProjectId, shot.id, { grid_image: res.url })
      ElMessage.success('上传成功')
    }
  } finally { loadingStore.stop() }
}

const handleDeleteGridImage = async (shot) => {
  shot.grid_image = ''
  await updateShot(store.currentProjectId, shot.id, { grid_image: '' })
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
</style>