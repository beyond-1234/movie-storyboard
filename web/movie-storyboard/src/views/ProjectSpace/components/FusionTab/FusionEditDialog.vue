<template>
  <el-dialog 
    v-model="visible" 
    :title="form.id ? '编辑融图任务' : '新建融图任务'" 
    width="1600px"
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
          
          <!-- 简单的添加占位符，提示去列表页添加 -->
          <div class="w-20 h-20 border border-dashed rounded flex flex-col items-center justify-center text-gray-400 bg-gray-50">
            <span class="text-xs text-center px-1">请在列表页添加元素</span>
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
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import { uploadBaseImage as uploadBaseImageApi, generateFusionImage, generateSceneImage } from '@/api/generation' 
import { createFusion, updateFusion } from '@/api/project' 
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'
import { ElMessage, ElNotification } from 'element-plus'
import { Delete, VideoCamera } from '@element-plus/icons-vue' 

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

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 重置表单方法
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

// 监听弹窗打开状态来初始化数据 (修复第二次点击不更新的问题)
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    if (props.initialData) {
      // 如果有传入数据，深拷贝赋值
      form.value = JSON.parse(JSON.stringify(props.initialData))
      // 确保数组字段存在
      if (!form.value.elements) form.value.elements = []
    } else {
      // 如果是新建，重置表单
      resetForm()
    }
  }
})

// 关闭时也可以调用一次重置，确保状态清理
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

const removeElement = (index) => {
  form.value.elements.splice(index, 1)
}

// 新增：生成底图
const handleGenerateBaseImage = async () => {
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请先在顶部选择生图模型')
  
  // 使用视觉描述或场景说明作为提示词
  const prompt = form.value.visual_description || form.value.scene_description || form.value.scene_prompt
  if (!prompt) return ElMessage.warning('生成底图需要画面描述或场景说明')

  try {
    // 复用场景图生成接口
    const res = await generateSceneImage({
      // 如果已保存任务有ID，尽量传ID以便后端更新
      // 但这里主要是为了生成图片，不一定要绑定scene_id，可以通过回调更新
      project_id: store.currentProjectId,
      scene_prompt: prompt, // 将描述直接作为 prompt 传入
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName,
      // 标记这是为融图生成的底图
      fusion_id: form.value.id 
    })
    
    if (res.success && res.status === 'queued') {
      ElNotification.success({ title: '任务已提交', message: '正在生成底图...' })
    }
  } catch (e) { console.error(e) }
}

// 新增：生成首帧
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

// 新增：生成尾帧
const handleGenerateEndImage = async () => {
  if (!form.value.id) return ElMessage.warning('请先保存任务')
  if (!store.genOptions.fusionProviderId) return ElMessage.warning('请先选择图生图模型')
  
  try {
    const res = await generateFusionImage({
      fusion_id: form.value.id,
      project_id: store.currentProjectId,
      fusion_prompt: form.value.end_frame_prompt,
      end_frame_prompt: form.value.end_frame_prompt, // 标记为尾帧
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