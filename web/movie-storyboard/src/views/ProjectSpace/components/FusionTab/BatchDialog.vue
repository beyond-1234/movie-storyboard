<template>
  <el-dialog v-model="visible" title="批量生成设置" width="400px">
    <el-form label-position="top">
      <el-form-item label="生成目标">
        <el-tag :type="tagType">{{ targetText }}</el-tag>
      </el-form-item>

      <el-form-item label="选择范围">
        <el-radio-group v-model="scope" class="flex flex-col gap-3">
          <el-radio label="all">全部任务</el-radio>
          
          <el-radio label="selected" :disabled="selection.length === 0">
            已选中的 {{ selection.length }} 个任务
            <span v-if="selection.length === 0" class="text-gray-400 text-xs ml-2">(请先在列表中勾选)</span>
          </el-radio>
          
          <el-radio label="missing">
            仅针对未生成的任务 (跳过已存在的)
          </el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleConfirm">开始生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps(['modelValue', 'type', 'selection'])
const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const scope = ref('all')

const targetText = computed(() => {
  const map = {
    prompt: '提示词 (Prompt)',
    image: '首帧融合图 (Start Frame)',
    end_image: '尾帧融合图 (End Frame)',
    video: '视频 (Video)'
  }
  return map[props.type] || props.type
})

const tagType = computed(() => {
  if (props.type === 'video') return 'danger'
  if (props.type === 'prompt') return 'warning'
  return 'success'
})

const handleConfirm = () => {
  emit('confirm', { scope: scope.value, target: props.type })
  visible.value = false
}
</script>