<template>
  <div 
    class="unified-image-card relative border rounded bg-gray-50 overflow-hidden group select-none transition-all duration-300 hover:shadow-md hover:border-blue-200"
    :class="[customClass]"
    :style="{ width: width, height: height }"
  >
    <!-- 1. 图片显示区域 -->
    <div v-if="src" class="w-full h-full relative">
      <el-image
        ref="imageRef"
        :src="src"
        :fit="fit"
        class="w-full h-full transition-transform duration-500 group-hover:scale-105"
        :preview-src-list="previewList || [src]"
        :initial-index="0"
        :z-index="9999"
        preview-teleported
        hide-on-click-modal
      >
        <template #error>
          <div class="flex flex-col items-center justify-center h-full text-gray-400 bg-gray-100">
            <el-icon :size="24"><Picture /></el-icon>
            <span class="text-[10px] mt-1">加载失败</span>
          </div>
        </template>
        <template #placeholder>
          <div class="flex items-center justify-center h-full bg-gray-100 text-gray-400">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
        </template>
      </el-image>

      <!-- 悬浮操作遮罩 -->
      <!-- 关键修改：@click.self="handlePreview" 确保点击遮罩空白处也能触发预览 -->
      <div 
        class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col items-center justify-center gap-2 z-10 cursor-zoom-in"
        @click.self="handlePreview"
      >
        
        <!-- 操作按钮组 -->
        <div class="flex items-center gap-2 transform translate-y-2 group-hover:translate-y-0 transition-transform duration-200 cursor-default">
          <el-tooltip v-if="enableGenerate" content="AI 重新生成" placement="top" :show-after="500">
            <el-button type="success" circle size="small" :icon="MagicStick" @click.stop="$emit('generate')" />
          </el-tooltip>

          <el-tooltip v-if="enableUpload" content="上传替换" placement="top" :show-after="500">
            <el-button type="primary" circle size="small" :icon="Upload" @click.stop="triggerUpload" />
          </el-tooltip>

          <el-tooltip content="放大查看" placement="top" :show-after="500">
            <el-button type="info" circle size="small" :icon="ZoomIn" @click.stop="handlePreview" />
          </el-tooltip>

          <el-tooltip v-if="enableDelete" content="删除图片" placement="top" :show-after="500">
            <el-button type="danger" circle size="small" :icon="Delete" @click.stop="$emit('delete')" />
          </el-tooltip>
        </div>

        <!-- 额外信息插槽 -->
        <div class="text-white text-[10px] mt-1 font-mono opacity-80 pointer-events-none" v-if="$slots.info">
          <slot name="info"></slot>
        </div>
      </div>
    </div>

    <!-- 2. 空状态区域 -->
    <div 
      v-else 
      class="w-full h-full flex flex-col items-center justify-center text-gray-400 cursor-pointer hover:bg-gray-100 transition-colors"
      @click="handleEmptyClick"
    >
      <slot name="empty">
        <el-icon :size="iconSize" class="mb-2 opacity-50"><component :is="emptyIcon" /></el-icon>
        <span class="text-xs scale-90">{{ placeholder }}</span>
      </slot>
      
      <div class="flex gap-2 mt-3" v-if="showEmptyActions">
        <el-button v-if="enableGenerate" size="small" type="success" plain :icon="MagicStick" class="!px-2" @click.stop="$emit('generate')">生成</el-button>
        <el-button v-if="enableUpload" size="small" type="primary" plain :icon="Upload" class="!px-2" @click.stop="triggerUpload">上传</el-button>
      </div>
    </div>

    <!-- 3. Loading 遮罩 -->
    <div v-if="loading" class="absolute inset-0 bg-white/80 z-20 flex flex-col items-center justify-center backdrop-blur-sm pointer-events-none">
      <el-icon class="is-loading text-blue-500" :size="24"><Loading /></el-icon>
      <span class="text-xs text-blue-500 mt-2 font-medium">{{ loadingText }}</span>
    </div>

    <!-- 隐藏的文件输入框 -->
    <input 
      type="file" 
      ref="fileInput" 
      class="hidden" 
      accept="image/png, image/jpeg, image/jpg, image/webp" 
      @change="handleFileChange" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Picture, MagicStick, Upload, Delete, ZoomIn, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  src: { type: String, default: '' },
  previewList: { type: Array, default: null }, 
  width: { type: String, default: '100%' },
  height: { type: String, default: '100%' },
  fit: { type: String, default: 'cover' },
  customClass: { type: String, default: '' },
  placeholder: { type: String, default: '暂无图片' },
  emptyIcon: { type: Object, default: Picture },
  iconSize: { type: Number, default: 24 },
  showEmptyActions: { type: Boolean, default: true }, 
  enableGenerate: { type: Boolean, default: true },
  enableUpload: { type: Boolean, default: true },
  enableDelete: { type: Boolean, default: true },
  loading: { type: Boolean, default: false },
  loadingText: { type: String, default: '处理中...' }
})

const emit = defineEmits(['generate', 'upload', 'delete', 'click-empty'])

const fileInput = ref(null)
const imageRef = ref(null)

const triggerUpload = () => {
  fileInput.value.value = ''
  fileInput.value.click()
}

const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 10MB')
    return
  }
  emit('upload', file)
}

// 核心修复：手动触发 Element Plus Image 的预览
const handlePreview = () => {
  // Element Plus 的 el-image 组件暴露了 showPreview 方法（在较新版本中）
  // 或者通过模拟点击内部的 img 或 mask 来触发
  if (imageRef.value) {
    // 尝试调用组件方法（如果版本支持）
    if (imageRef.value.showPreview) {
      imageRef.value.showPreview()
    } else {
      // 降级方案：找到内部的预览触发区域并点击
      // 通常 el-image 点击图片本身就会触发预览
      // 但由于我们有遮罩，需要确保点击事件能穿透或者我们手动控制 Viewer 的显示状态
      // 最稳妥的方法是使用 el-image-viewer 组件，但为了简单，这里尝试触发 clickHandler
      if(imageRef.value.clickHandler) {
          imageRef.value.clickHandler()
      }
    }
  }
}

const handleEmptyClick = () => {
  if (props.enableUpload && !props.showEmptyActions) {
    triggerUpload()
  } else {
    emit('click-empty')
  }
}
</script>

<style scoped>
:deep(.el-image__inner) {
  vertical-align: top;
}
</style>