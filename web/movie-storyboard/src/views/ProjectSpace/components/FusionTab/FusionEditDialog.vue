<template>
  <el-dialog 
    v-model="visible" 
    :title="form.id ? '编辑融图任务' : '新建融图任务'" 
    width="900px"
    @close="handleClose"
    top="5vh"
  >
    <el-form :model="form" label-width="100px" size="default">
      
      <!-- 第一行：索引信息 -->
      <div class="grid grid-cols-3 gap-4">
        <el-form-item label="场次">
          <el-input v-model="form.scene" placeholder="例如: 1" />
        </el-form-item>
        <el-form-item label="镜号">
          <el-input v-model="form.shot_number" placeholder="例如: 1" />
        </el-form-item>
        <el-form-item label="关联分镜">
          <el-select v-model="form.shot_id" placeholder="选择关联分镜" @change="handleShotChange" class="w-full" clearable filterable>
            <el-option 
              v-for="s in store.shotList" 
              :key="s.id" 
              :label="`场${s.scene}-镜${s.shot_number}`" 
              :value="s.id" 
            />
          </el-select>
        </el-form-item>
      </div>

      <!-- 第二行：文本描述 -->
      <el-divider content-position="left">分镜描述</el-divider>
      
      <el-form-item label="场景说明">
        <el-input v-model="form.scene_description" type="textarea" :rows="2" placeholder="场景的整体描述..." />
      </el-form-item>

      <el-form-item label="画面内容">
        <el-input v-model="form.visual_description" type="textarea" :rows="3" placeholder="画面中发生了什么..." />
      </el-form-item>

      <div class="grid grid-cols-2 gap-4">
        <el-form-item label="台词">
          <el-input v-model="form.dialogue" type="textarea" :rows="2" placeholder="角色对白..." />
        </el-form-item>
        <el-form-item label="声音/音效">
          <el-input v-model="form.audio_description" type="textarea" :rows="2" placeholder="背景音、音效..." />
        </el-form-item>
      </div>

      <!-- 第三行：素材附件 -->
      <el-divider content-position="left">素材附件</el-divider>

      <el-form-item label="底图" required>
        <div class="flex items-center gap-4">
          <UnifiedImageCard
            :src="form.base_image"
            width="160px"
            height="100px"
            fit="cover"
            placeholder="上传底图"
            :enable-delete="!!form.base_image"
            :enable-generate="true"
            @generate="handleGenerateBaseImage"
            @upload="handleBaseUpload"
            @delete="form.base_image = ''"
          />
          <div class="text-xs text-gray-400">
            <p>支持 JPG/PNG 格式</p>
            <p>或使用 AI 重新生成</p>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="元素列表">
        <div class="flex flex-wrap gap-3">
          <UnifiedImageCard
            v-for="(el, index) in form.elements"
            :key="el.id || index"
            :src="el.image_url"
            width="80px"
            height="80px"
            fit="cover"
            :placeholder="el.name"
            :enable-generate="false"
            :enable-upload="false"
            :enable-delete="true"
            @delete="removeElement(index)"
          >
            <template #info>{{ el.name }}</template>
          </UnifiedImageCard>
          
          <!-- 添加元素按钮 -->
          <div 
            class="w-20 h-20 border border-dashed border-gray-300 rounded flex flex-col items-center justify-center text-gray-400 bg-gray-50 hover:border-blue-400 hover:text-blue-500 cursor-pointer transition-colors"
            @click="openElementDialog"
          >
            <el-icon :size="24"><Plus /></el-icon>
            <span class="text-xs mt-1">添加元素</span>
          </div>
        </div>
      </el-form-item>

      <!-- 第四行：生成结果 -->
      <el-divider content-position="left">生成结果</el-divider>

      <div class="grid grid-cols-2 gap-6">
        <!-- 首帧部分 -->
        <div class="bg-gray-50 p-3 rounded border border-gray-100">
          <div class="font-bold text-gray-700 mb-2 text-sm">首帧 (Start Frame)</div>
          <el-form-item label-width="0">
            <el-input 
              type="textarea" 
              v-model="form.fusion_prompt" 
              :rows="4" 
              placeholder="首帧提示词..." 
              class="mb-2"
            />
            <UnifiedImageCard
              :src="form.result_image"
              width="100%"
              height="180px"
              fit="contain"
              placeholder="首帧结果图"
              :enable-delete="!!form.result_image"
              :enable-generate="true" 
              @generate="handleGenerateImage"
              @upload="(file) => handleResultUpload(file, 'result_image')"
              @delete="form.result_image = ''"
            />
          </el-form-item>
        </div>

        <!-- 尾帧部分 -->
        <div class="bg-gray-50 p-3 rounded border border-gray-100">
          <div class="font-bold text-gray-700 mb-2 text-sm">尾帧 (End Frame)</div>
          <el-form-item label-width="0">
            <el-input 
              type="textarea" 
              v-model="form.end_frame_prompt" 
              :rows="4" 
              placeholder="尾帧提示词..." 
              class="mb-2"
            />
            <UnifiedImageCard
              :src="form.end_frame_image"
              width="100%"
              height="180px"
              fit="contain"
              placeholder="尾帧结果图"
              :enable-delete="!!form.end_frame_image"
              :enable-generate="true"
              @generate="handleGenerateEndImage"
              @upload="(file) => handleResultUpload(file, 'end_frame_image')"
              @delete="form.end_frame_image = ''"
            />
          </el-form-item>
        </div>
      </div>

      <el-form-item label="最终视频" class="mt-4">
        <div v-if="form.video_url" class="w-full max-w-md relative group">
          <video :src="form.video_url" controls class="w-full rounded border bg-black"></video>
          <el-button 
            type="danger" 
            circle 
            size="small" 
            :icon="Delete" 
            class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
            @click="form.video_url = ''"
          />
        </div>
        <div v-else class="text-gray-400 text-sm flex items-center h-10">
          <el-icon class="mr-1"><VideoCamera /></el-icon> 尚未生成视频
        </div>
      </el-form-item>

    </el-form>
    
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>

    <!-- 嵌套的元素添加弹窗 -->
    <!-- 注意：为了避免 form 引用混乱，这里传入一个临时的 fusion 对象 -->
    <ElementDialog 
      v-model="elementDialogVisible" 
      :fusion="tempFusionForElement" 
      @success="handleElementSuccess" 
    />
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import { uploadBaseImage as uploadBaseImageApi, generateFusionImage, generateSceneImage } from '@/api/generation' 
import { createFusion, updateFusion } from '@/api/project' 
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'
import ElementDialog from './ElementDialog.vue' // 引入 ElementDialog
import { ElMessage, ElNotification } from 'element-plus'
import { Delete, VideoCamera, Plus } from '@element-plus/icons-vue' 

const props = defineProps(['modelValue', 'initialData'])
const emit = defineEmits(['update:modelValue', 'success'])

const store = useProjectStore()
const loadingStore = useLoadingStore()

const form = ref({
  scene: '', shot_number: '', shot_id: '',
  scene_description: '', visual_description: '', dialogue: '', audio_description: '',
  base_image: '', elements: [], 
  fusion_prompt: '', result_image: '', 
  end_frame_prompt: '', end_frame_image: '',
  video_url: ''
})

const elementDialogVisible = ref(false)
// 创建一个临时对象传给 ElementDialog，用于接收新元素
// ElementDialog 会尝试修改 fusion.elements，所以我们需要传递一个包含 elements 数组的对象
const tempFusionForElement = computed(() => ({
  elements: form.value.elements
}))

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const resetForm = () => {
  form.value = { 
    scene: '', shot_number: '', shot_id: '', 
    scene_description: '', visual_description: '', dialogue: '', audio_description: '',
    base_image: '', elements: [], 
    fusion_prompt: '', result_image: '', 
    end_frame_prompt: '', end_frame_image: '',
    video_url: ''
  }
}

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    if (props.initialData) {
      form.value = JSON.parse(JSON.stringify(props.initialData))
      if (!form.value.elements) form.value.elements = []
    } else {
      resetForm()
    }
  }
})

const handleClose = () => {
  resetForm()
}

const handleShotChange = (shotId) => {
  const shot = store.shotList.find(s => s.id === shotId)
  if (shot) {
    form.value.scene = shot.scene
    form.value.shot_number = shot.shot_number
    form.value.scene_description = shot.scene_description
    form.value.visual_description = shot.visual_description
    form.value.dialogue = shot.dialogue
    form.value.audio_description = shot.audio_description
  }
}

const uploadImage = async (file, fieldName) => {
  const fd = new FormData()
  fd.append('file', file)
  if (form.value.id) fd.append('fusion_id', form.value.id)
  
  loadingStore.start('上传中', '正在上传图片...')
  try {
    const res = await uploadBaseImageApi(fd)
    if (res.success) {
       form.value[fieldName] = res.url
       ElMessage.success('上传成功')
    }
  } catch (e) {
    console.error(e)
  } finally {
    loadingStore.stop()
  }
}

const handleBaseUpload = (file) => uploadImage(file, 'base_image')
const handleResultUpload = (file, field) => uploadImage(file, field)

// 元素操作
const openElementDialog = () => {
  elementDialogVisible.value = true
}

const handleElementSuccess = (updatedFusion) => {
  // ElementDialog 会返回更新后的 fusion 对象（这里是我们传进去的 tempFusion）
  // 或者它直接修改了引用。
  // 我们手动把新元素同步回 form.elements
  form.value.elements = updatedFusion.elements
  // 注意：ElementDialog 内部可能会调用 API 更新后端，
  // 但对于新建任务（没有ID），ElementDialog 可能无法保存。
  // 我们需要确保 ElementDialog 支持纯前端添加模式，或者仅在 submit 时统一保存。
  // 假设 ElementDialog 已经适配了（见下文分析），或者我们在这里做兼容。
}

const removeElement = (index) => {
  form.value.elements.splice(index, 1)
}

// AI 生成逻辑 (底图、首帧、尾帧)
const handleGenerateBaseImage = async () => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请先在顶部选择生图模型')
  const prompt = form.value.visual_description || form.value.scene_description || form.value.scene_prompt
  if (!prompt) return ElMessage.warning('生成底图需要画面描述或场景说明')

  try {
    const res = await generateSceneImage({
      project_id: store.currentProjectId,
      scene_prompt: prompt,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName,
      fusion_id: form.value.id 
    })
    if (res.success && res.status === 'queued') {
      ElNotification.success({ title: '任务已提交', message: '正在生成底图...' })
    }
  } catch (e) { console.error(e) }
}

const handleGenerateImage = async () => {
  if (!form.value.id) return ElMessage.warning('请先保存任务')
  if (!store.genOptions.fusionProviderId) return ElMessage.warning('请先选择图生图模型')
  if (!form.value.base_image) return ElMessage.warning('需要底图')
  
  try {
    const res = await generateFusionImage({
      fusion_id: form.value.id,
      project_id: store.currentProjectId,
      fusion_prompt: form.value.fusion_prompt,
      provider_id: store.genOptions.fusionProviderId,
      model_name: store.genOptions.fusionModelName
    })
    if (res.success) ElNotification.success({ title: '任务已提交', message: '首帧生成中...' })
  } catch (e) { console.error(e) }
}

const handleGenerateEndImage = async () => {
  if (!form.value.id) return ElMessage.warning('请先保存任务')
  if (!store.genOptions.fusionProviderId) return ElMessage.warning('请先选择图生图模型')
  
  try {
    const res = await generateFusionImage({
      fusion_id: form.value.id,
      project_id: store.currentProjectId,
      fusion_prompt: form.value.end_frame_prompt,
      end_frame_prompt: form.value.end_frame_prompt, 
      provider_id: store.genOptions.fusionProviderId,
      model_name: store.genOptions.fusionModelName
    })
    if (res.success) ElNotification.success({ title: '任务已提交', message: '尾帧生成中...' })
  } catch (e) { console.error(e) }
}

const submit = async () => {
  try {
    if (form.value.id) {
        await updateFusion(store.currentProjectId, form.value.id, form.value)
    } else {
        await createFusion(store.currentProjectId, form.value)
    }
    
    ElMessage.success('保存成功')
    visible.value = false
    emit('success')
  } catch (e) {
    console.error(e)
  }
}
</script>