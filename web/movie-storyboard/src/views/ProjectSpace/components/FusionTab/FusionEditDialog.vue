<template>
  <el-dialog 
    v-model="visible" 
    :title="form.id ? '编辑融图任务' : '新建融图任务'" 
    width="800px"
    @close="resetForm"
  >
    <el-form :model="form" label-width="100px" size="small">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="场次"><el-input v-model="form.scene" /></el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="镜号"><el-input v-model="form.shot_number" /></el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="关联分镜">
            <el-select v-model="form.shot_id" placeholder="选择分镜" @change="handleShotChange">
              <el-option v-for="s in store.shotList" :key="s.id" :label="`场${s.scene}-镜${s.shot_number}`" :value="s.id" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="底图" required>
        <div class="flex items-center gap-4">
          <div v-if="form.base_image" class="relative w-32 h-20 border rounded overflow-hidden group">
            <el-image :src="form.base_image" fit="cover" class="w-full h-full" />
            <div class="absolute inset-0 bg-black/50 hidden group-hover:flex items-center justify-center cursor-pointer text-white" @click="form.base_image = ''">
              <el-icon><Delete /></el-icon>
            </div>
          </div>
          <el-upload 
            action="#" 
            :http-request="uploadBaseImage" 
            :show-file-list="false"
            accept="image/*"
          >
            <el-button icon="Upload">上传底图</el-button>
          </el-upload>
        </div>
      </el-form-item>

      <el-form-item label="提示词">
        <el-input type="textarea" v-model="form.fusion_prompt" :rows="4" placeholder="描述画面内容..." />
      </el-form-item>

      <el-form-item label="结果图">
        <el-image v-if="form.result_image" :src="form.result_image" class="w-40 h-24 border rounded" />
        <span v-else class="text-gray-400">尚未生成</span>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" plain @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import request from '@/api'
import { ElMessage } from 'element-plus'

const props = defineProps(['modelValue', 'initialData'])
const emit = defineEmits(['update:modelValue', 'success'])

const store = useProjectStore()
const form = ref({
  scene: '', shot_number: '', shot_id: '',
  base_image: '', fusion_prompt: '', result_image: '',
  elements: []
})

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const resetForm = () => {
  form.value = { scene: '', shot_number: '', shot_id: '', base_image: '', fusion_prompt: '', result_image: '', elements: [] }
}

watch(() => props.initialData, (val) => {
  if (val) form.value = JSON.parse(JSON.stringify(val))
  else resetForm()
}, { immediate: true })

const handleShotChange = (shotId) => {
  const shot = store.shotList.find(s => s.id === shotId)
  if (shot) {
    form.value.scene = shot.scene
    form.value.shot_number = shot.shot_number
    // 可以在这里做“是否同步底图”的询问逻辑
  }
}

const uploadBaseImage = async ({ file }) => {
  const fd = new FormData()
  fd.append('file', file)
  if (form.value.id) fd.append('fusion_id', form.value.id)
  
  const res = await request.post('/upload/base_image', fd, { headers: { 'Content-Type': 'multipart/form-data' }})
  form.value.base_image = res.url
}

const submit = async () => {
  const url = form.value.id 
    ? `/projects/${store.currentProjectId}/fusions/${form.value.id}`
    : `/projects/${store.currentProjectId}/fusions`
  
  const method = form.value.id ? 'put' : 'post'
  
  await request[method](url, form.value)
  ElMessage.success('保存成功')
  visible.value = false
  emit('success')
}
</script>