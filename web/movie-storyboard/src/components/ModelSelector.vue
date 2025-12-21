<template>
  <div class="flex items-center gap-2">
    <span class="text-xs font-bold text-gray-600">{{ label }}</span>
    <el-select 
      :model-value="provider" 
      @update:model-value="val => $emit('update:provider', val)"
      placeholder="供应商" 
      size="small" 
      class="w-32"
      @change="handleProviderChange"
    >
      <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
    </el-select>
    
    <el-select 
      :model-value="model" 
      @update:model-value="val => $emit('update:model', val)"
      placeholder="模型" 
      size="small" 
      class="w-40"
    >
      <el-option v-for="m in currentModels" :key="m.name" :label="m.name" :value="m.name" />
    </el-select>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import request from '@/api'

const props = defineProps({
  provider: String,
  model: String,
  type: { type: String, default: 'image' }, // image, video, text, image_fusion
  label: { type: String, default: '模型' }
})

const emit = defineEmits(['update:provider', 'update:model'])

const providers = ref([])

// 获取设置数据（通常在 Store 里获取一次，这里简化为组件内获取）
const fetchSettings = async () => {
  providers.value = await request.get('/settings')
}

const currentModels = computed(() => {
  const p = providers.value.find(x => x.id === props.provider)
  if (!p || !p.models) return []
  return p.models.filter(m => m.type === props.type)
})

const handleProviderChange = () => {
  // 切换供应商时，自动选择第一个可用模型
  if (currentModels.value.length > 0) {
    emit('update:model', currentModels.value[0].name)
  } else {
    emit('update:model', '')
  }
}

onMounted(fetchSettings)
</script>