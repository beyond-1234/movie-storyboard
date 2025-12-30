<template>
  <div class="h-full flex flex-col bg-gray-50">
    <!-- 顶部操作栏 -->
    <div class="h-14 border-b border-gray-200 flex items-center px-6 justify-between bg-white shadow-sm z-10 shrink-0">
      <div class="flex items-center gap-6">
        <div class="text-sm text-gray-500 font-medium flex items-center">
          <span class="bg-blue-50 text-blue-600 px-2 py-1 rounded text-xs mr-2 font-bold">分镜</span>
          <span>共 {{ store.shotList.length }} 镜</span>
        </div>
      </div>
      <div class="space-x-3 flex items-center">
        <el-button @click="$emit('prev')" class="text-gray-500 hover:text-gray-800 text-sm px-3 font-medium">上一步</el-button>
        <el-button type="primary" plain @click="refreshData" :icon="Refresh">刷新数据</el-button>
        <el-button @click="$emit('next')" class="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-1.5 rounded shadow-sm transition-colors">下一步 (剪辑)</el-button>
      </div>
    </div>

    <!-- 配置栏 -->
    <div class="h-14 border-b border-gray-200 flex items-center px-6 justify-between bg-white shadow-sm z-10 shrink-0">
      <div class="flex items-center gap-6">
        <div class="flex items-center gap-2">
          <el-icon class="text-gray-500"><SetUp /></el-icon>
          <span class="text-sm font-bold text-gray-700">AI 模型配置</span>
        </div>
        <div class="w-px h-5 bg-gray-200"></div>
        <div class="flex items-center gap-3">
          <ModelSelector type="text" label="文本" v-model:provider="store.genOptions.textProviderId" v-model:model="store.genOptions.textModelName" />
          <ModelSelector type="image" label="绘图" v-model:provider="store.genOptions.imageProviderId" v-model:model="store.genOptions.imageModelName" />
          <ModelSelector type="video" label="视频" v-model:provider="store.genOptions.videoProviderId" v-model:model="store.genOptions.videoModelName" />
        </div>
      </div>
    </div>

    <!-- 主列表 -->
    <div class="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
      <div v-for="(shot, index) in store.shotList" :key="shot.id" class="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow">
        
        <!-- 分镜信息头部 -->
        <div class="flex items-center justify-between mb-6 border-b border-gray-100 pb-4">
          <div class="flex items-center gap-4">
             <div class="flex flex-col items-center justify-center bg-gray-100 w-12 h-12 rounded-lg">
               <span class="text-xs text-gray-400">SCENE</span>
               <span class="text-xl font-bold text-gray-700">{{ shot.scene }}</span>
             </div>
             <div>
                <p class="text-gray-800 font-bold whitespace-pre-wrap break-words">{{ shot.visual_description || '暂无画面描述' }}</p>
                <div class="flex gap-2 mt-1">
                   <span class="text-xs text-gray-400">镜号: {{ shot.shot_number }} | {{ shot.shot_size || 'Unknown' }} | {{ shot.duration }}s</span>
                </div>
                <div class="flex gap-2 mt-1" v-if="shot.dialogue">
                   <span class="text-xs text-blue-500 font-medium">台词：“{{ shot.dialogue }}”</span>
                </div>
             </div>
          </div>
        </div>

        <!-- 三步生成流程 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <!-- Step 2.1: 场景底图 -->
          <div class="space-y-3 group flex flex-col">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-blue-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span> Step 2.1: 场景底图
              </span>
              <el-button link type="primary" size="small" @click="handleGenScenePrompt(shot)" :loading="shot._loadingScenePrompt">
                 生成Prompt
              </el-button>
            </div>
            <el-input type="textarea" class="w-full text-sm" :rows="8" resize="none" v-model="shot.scene_prompt" placeholder="场景提示词..." />
            <div class="flex-1 min-h-[200px]">
               <UnifiedImageCard
                 :src="shot.scene_image"
                 placeholder="场景底图"
                 :enable-generate="true"
                 :enable-upload="true"
                 :enable-delete="!!shot.scene_image"
                 @generate="handleGenSceneImage(shot)"
                 @upload="(file) => handleSceneUpload(shot, file)"
                 @delete="handleDeleteSceneImage(shot)"
               />
            </div>
          </div>

          <!-- Step 2.2: 动作九宫格 -->
          <div class="space-y-3 group flex flex-col">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-purple-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-purple-500"></span> Step 2.2: 动作九宫格
              </span>
              <el-button link type="primary" size="small" @click="handleGenGridPrompt(shot)" :loading="shot._loadingGridPrompt">
                 生成Prompt
              </el-button>
            </div>
            <el-input type="textarea" class="w-full text-sm" :rows="8" resize="none" v-model="shot.grid_prompt" placeholder="九宫格提示词..." />
            <div class="flex-1 min-h-[200px]">
               <UnifiedImageCard
                 :src="shot.grid_image"
                 placeholder="9宫格预览"
                 :enable-generate="true"
                 :enable-upload="true"
                 :enable-delete="!!shot.grid_image"
                 @generate="handleGenGridImage(shot)"
                 @upload="(file) => handleGridUpload(shot, file)"
                 @delete="handleDeleteGridImage(shot)"
               />
            </div>
          </div>

          <!-- Step 2.3: 动态视频 -->
          <div class="space-y-3 group flex flex-col">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-green-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-green-500"></span> Step 2.3: 动态视频
              </span>
              <el-button link type="primary" size="small" @click="handleGenVideoPrompt(shot)" :loading="shot._loadingVideoPrompt">
                 生成Prompt
              </el-button>
            </div>
            <el-input type="textarea" class="w-full text-sm" :rows="8" resize="none" v-model="shot.video_prompt" placeholder="视频提示词..." />
            <div class="flex-1 min-h-[200px] bg-gray-100 rounded-lg border border-gray-200 relative overflow-hidden flex items-center justify-center">
               <video v-if="shot.video_url" :src="shot.video_url" controls class="w-full h-full object-cover"></video>
               <div v-else class="text-gray-400 text-xs flex flex-col items-center gap-2">
                 <span class="text-2xl">🎬</span>
                 <span>等待生成</span>
               </div>
               <div class="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-end p-2 pointer-events-none">
                  <el-button 
                    class="bg-green-600 text-white text-xs px-3 py-1.5 rounded shadow-lg pointer-events-auto hover:bg-green-700 border-none"
                    :disabled="!shot.video_prompt && !shot.grid_image && !shot.scene_image"
                    @click="handleGenVideo(shot)"
                  >
                    {{ shot.video_url ? '重新生成' : '生成视频' }}
                  </el-button>
               </div>
            </div>
          </div>

        </div>
      </div>
      <el-empty v-if="store.shotList.length === 0" description="暂无分镜数据" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'
import ModelSelector from '@/components/ModelSelector.vue'
import { Refresh, SetUp } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'

// API 对接
import { 
  generateScenePrompt, 
  generateSceneImage, 
  generateGridPrompt,
  generateGridImage,
  generateVideoPrompt,
  uploadSceneImage, 
  uploadGridImage
} from '@/api/generation'
import { updateShot } from '@/api/project'

const props = defineProps(['projectId'])
const emit = defineEmits(['next', 'prev'])

const store = useProjectStore()
const loadingStore = useLoadingStore()

onMounted(async () => {
  await refreshData()
})

const refreshData = async () => {
  if (store.currentProjectId) {
    loadingStore.start('加载中', '正在同步分镜数据...')
    try {
      await store.fetchShots()
      await store.fetchCharacters()
    } finally {
      loadingStore.stop()
    }
  }
}

// --- 通用工具 ---

const getShotCharNames = (shot) => {
  if (!shot.characters) return []
  return shot.characters.map(c => {
    const id = typeof c === 'object' ? c.id : c
    const charObj = store.characterList.find(x => x.id === id)
    return charObj ? charObj.name : '未知角色'
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

// --- Step 2.1: 场景逻辑 ---

const handleGenScenePrompt = async (shot) => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请配置文本模型')
  shot._loadingScenePrompt = true
  try {
    const res = await generateScenePrompt({
      scene_id: shot.id,
      project_id: store.currentProjectId,
      scene_description: shot.scene_description || shot.visual_description,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    if (res.success) {
      ElNotification.success({ title: '任务提交成功', message: '场景提示词正在后台生成中...' })
    }
  } finally { shot._loadingScenePrompt = false }
}

const handleGenSceneImage = async (shot) => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请配置绘图模型')
  if (!shot.scene_prompt) return ElMessage.warning('请先生成场景提示词')
  try {
    const res = await generateSceneImage({
      scene_id: shot.id,
      project_id: store.currentProjectId,
      scene_prompt: shot.scene_prompt,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    if (res.success) {
      ElNotification.success({ title: '任务提交成功', message: '场景底图已加入生成队列' })
    }
  } catch (e) { console.error(e) }
}

const handleSceneUpload = async (shot, file) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('scene_id', shot.id)
  try {
    const res = await uploadSceneImage(fd)
    if (res.success) {
      shot.scene_image = res.url
      await updateShot(store.currentProjectId, shot.id, { scene_image: res.url })
      ElMessage.success('场景图上传成功')
    }
  } catch (e) { ElMessage.error('上传失败') }
}

const handleDeleteSceneImage = async (shot) => {
  shot.scene_image = ''
  await updateShot(store.currentProjectId, shot.id, { scene_image: '' })
}

// --- Step 2.2: 九宫格逻辑 ---

const handleGenGridPrompt = async (shot) => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请配置文本模型')
  shot._loadingGridPrompt = true
  try {
    // 修复点：添加 project_id 和 shot_id
    const res = await generateGridPrompt({
      shot_id: shot.id,
      project_id: store.currentProjectId,
      scene_description: shot.scene_description || shot.visual_description,
      shot_description: shot.visual_description,
      character_names: getShotCharNames(shot),
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    if (res.success) {
      ElNotification.success({ title: '任务提交成功', message: '九宫格提示词正在后台生成中...' })
    }
  } finally { shot._loadingGridPrompt = false }
}

const handleGenGridImage = async (shot) => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请配置绘图模型')
  if (!shot.grid_prompt) return ElMessage.warning('请先生成提示词')
  try {
    const res = await generateGridImage({
      shot_id: shot.id,
      project_id: store.currentProjectId,
      grid_prompt: shot.grid_prompt,
      base_image_url: shot.scene_image,
      character_images: getShotCharImages(shot),
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    if (res.success) {
      ElNotification.success({ title: '任务提交成功', message: '九宫格生成任务排队中...' })
    }
  } catch(e) { console.error(e) }
}

const handleGridUpload = async (shot, file) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('shot_id', shot.id)
  try {
    const res = await uploadGridImage(fd)
    if (res.success) {
      shot.grid_image = res.url 
      await updateShot(store.currentProjectId, shot.id, { grid_image: res.url })
      ElMessage.success('上传成功')
    }
  } catch (e) { ElMessage.error('上传失败') }
}

const handleDeleteGridImage = async (shot) => {
  shot.grid_image = ''
  await updateShot(store.currentProjectId, shot.id, { grid_image: '' })
}

// --- Step 2.3: 视频逻辑 ---

const handleGenVideoPrompt = async (shot) => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请配置文本模型')
  shot._loadingVideoPrompt = true
  try {
    // 修复点：添加 project_id 
    const res = await generateVideoPrompt({
      shot_id: shot.id,
      project_id: store.currentProjectId,
      scene_description: shot.scene_description || shot.visual_description,
      shot_description: shot.visual_description,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    if (res.success) {
      ElNotification.success({ title: '任务提交成功', message: '视频动态提示词正在后台生成中...' })
    }
  } finally { shot._loadingVideoPrompt = false }
}

const handleGenVideo = async (shot) => {
  if (!store.genOptions.videoProviderId) return ElMessage.warning('请配置视频模型')
  if (!shot.video_prompt) return ElMessage.warning('请先生成视频提示词')
  
  try {
    const res = await store.dispatchGenerateVideo(shot)
    if (res.success) {
      ElNotification.success({ title: '任务提交成功', message: '动态视频正在排队生成...' })
    }
  } catch (e) {
    ElMessage.error('视频生成请求失败')
  }
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 3px; }
.custom-scrollbar:hover::-webkit-scrollbar-thumb { background-color: #d1d5db; }
</style>