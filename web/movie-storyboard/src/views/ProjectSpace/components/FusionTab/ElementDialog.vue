<template>
  <el-dialog v-model="visible" title="添加元素" width="500px" destroy-on-close>
    <el-form :model="form" label-width="80px" @submit.prevent="submit">
      <el-form-item label="元素名称" required>
        <el-input v-model="form.name" placeholder="例如：孙悟空、红色跑车" />
      </el-form-item>
      
      <el-form-item label="添加方式">
        <el-radio-group v-model="form.type">
          <el-radio label="character">选择角色</el-radio>
          <el-radio label="upload">上传图片</el-radio>
          <el-radio label="generate">AI 生成</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 选择角色 -->
      <div v-if="form.type === 'character'">
        <el-form-item label="选择角色">
          <el-select v-model="form.character_id" placeholder="请选择" class="w-full" @change="handleCharChange">
            <el-option v-for="c in store.characterList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <div v-if="previewUrl" class="ml-20 mb-4">
          <el-image :src="previewUrl" class="w-24 h-24 border rounded" fit="cover" />
        </div>
      </div>

      <!-- 上传图片 -->
      <div v-if="form.type === 'upload'">
        <el-form-item label="图片文件">
           <input type="file" ref="fileInput" accept="image/*" @change="handleFileSelected" />
        </el-form-item>
        <div v-if="previewUrl" class="ml-20 mb-4">
          <el-image :src="previewUrl" class="w-24 h-24 border rounded" fit="cover" />
        </div>
      </div>

      <!-- AI 生成 -->
      <div v-if="form.type === 'generate'">
        <el-form-item label="提示词">
          <el-input v-model="form.prompt" type="textarea" :rows="3" placeholder="描述要生成的元素外观..." />
        </el-form-item>
        <el-form-item>
           <el-button type="primary" plain size="small" :loading="generating" @click="generateElement">生成预览</el-button>
        </el-form-item>
        <div v-if="previewUrl" class="ml-20 mb-4">
          <el-image :src="previewUrl" class="w-24 h-24 border rounded" fit="cover" />
        </div>
      </div>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submit" :disabled="!canSubmit">确定添加</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { uploadElementImage, generateElementImage } from '@/api/generation'
import { updateFusion } from '@/api/project'
import { ElMessage } from 'element-plus'

const props = defineProps(['modelValue', 'fusion'])
const emit = defineEmits(['update:modelValue', 'success'])
const store = useProjectStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const form = ref({ name: '', type: 'character', character_id: '', prompt: '' })
const previewUrl = ref('')
const selectedFile = ref(null)
const generating = ref(false)
const fileInput = ref(null)

// Reset on open
watch(() => props.modelValue, (val) => {
  if (val) {
    form.value = { name: '', type: 'character', character_id: '', prompt: '' }
    previewUrl.value = ''
    selectedFile.value = null
  }
})

const canSubmit = computed(() => form.value.name && previewUrl.value)

// Handlers
const handleCharChange = (id) => {
  const char = store.characterList.find(c => c.id === id)
  if (char) {
    form.value.name = char.name // 自动填充名字
    previewUrl.value = char.image_url
  }
}

const handleFileSelected = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
    previewUrl.value = URL.createObjectURL(file) // 本地预览
  }
}

const generateElement = async () => {
  if (!form.value.prompt) return ElMessage.warning('请输入提示词')
  if (!store.genOptions.imageProviderId) return ElMessage.warning('请选择生图模型')
  
  generating.value = true
  try {
    // 生成是一个同步/快速接口，或者返回 URL
    const res = await generateElementImage({
      prompt: form.value.prompt,
      provider_id: store.genOptions.imageProviderId,
      model_name: store.genOptions.imageModelName
    })
    if (res.success) {
      previewUrl.value = res.url
    }
  } finally {
    generating.value = false
  }
}

const submit = async () => {
  let finalUrl = previewUrl.value

  // 如果是上传类型，需要先上传文件拿到 URL
  if (form.value.type === 'upload' && selectedFile.value) {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    // 假设有一个通用上传接口或元素上传接口
    const res = await uploadElementImage(fd) 
    if (res.success) finalUrl = res.url
    else return ElMessage.error('图片上传失败')
  }

  // 构造新元素对象
  const newElement = {
    id: `el_${Date.now()}`,
    name: form.value.name,
    image_url: finalUrl,
    type: form.value.type,
    character_id: form.value.character_id
  }

  // 更新 Fusion 数据
  const updatedElements = [...(props.fusion.elements || []), newElement]
  
  try {
    await updateFusion(store.currentProjectId, props.fusion.id, { elements: updatedElements })
    
    // 更新本地状态
    const newFusion = { ...props.fusion, elements: updatedElements }
    emit('success', newFusion)
    visible.value = false
    ElMessage.success('元素添加成功')
  } catch (e) {
    console.error(e)
  }
}
</script>