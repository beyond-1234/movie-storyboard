<template>
  <el-dialog 
    v-model="visible" 
    title="模型供应商管理" 
    width="900px" 
    destroy-on-close
    :close-on-click-modal="false"
    class="settings-dialog"
    @open="fetchSettings"
  >
    <div class="flex h-[550px] border border-gray-200 rounded overflow-hidden">
      <!-- 左侧侧边栏：供应商列表 -->
      <div class="w-64 bg-gray-50 border-r border-gray-200 flex flex-col p-3">
        <el-button type="primary" plain class="w-full mb-3 shadow-sm" icon="Plus" @click="initNewProvider">
          新增供应商
        </el-button>
        
        <div class="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
          <div 
            v-for="p in providers" 
            :key="p.id"
            class="px-3 py-2.5 rounded cursor-pointer flex items-center justify-between text-sm transition-all duration-200 group"
            :class="editingProvider?.id === p.id ? 'bg-white shadow-sm text-blue-600 font-medium border border-blue-100' : 'hover:bg-gray-200 text-gray-700'"
            @click="selectProvider(p)"
          >
            <div class="flex items-center gap-3 overflow-hidden">
               <div 
                 class="w-6 h-6 rounded flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm" 
                 :style="{ background: getProviderColor(p.type) }"
               >
                 {{ p.name.charAt(0).toUpperCase() }}
               </div>
               <span class="truncate">{{ p.name }}</span>
            </div>
            <el-icon :class="editingProvider?.id === p.id ? 'text-blue-500' : 'text-gray-300 group-hover:text-gray-500'"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>

      <!-- 右侧内容区：编辑表单 -->
      <div class="flex-1 flex flex-col h-full bg-white">
        <div v-if="editingProvider" class="flex-1 overflow-y-auto p-6 custom-scrollbar">
          <el-form label-position="top" size="default">
            
            <!-- 基础信息卡片 -->
            <div class="bg-gray-50 p-4 rounded-lg border border-gray-100 mb-6">
              <div class="text-sm font-bold text-gray-700 mb-4 flex items-center gap-2">
                <el-icon><SetUp /></el-icon> 基础配置
              </div>
              <el-form-item label="供应商名称" required>
                <el-input v-model="editingProvider.name" placeholder="例如：我的 DeepSeek" />
              </el-form-item>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="类型" required>
                    <el-select v-model="editingProvider.type" class="w-full" @change="handleTypeChange">
                      <el-option label="Aliyun DashScope (通义)" value="aliyun" />
                      <el-option label="SiliconFlow (硅基流动)" value="siliconflow" />
                      <el-option label="RunningHub" value="runninghub" />
                      <el-option label="VIDU Studio" value="vidu" />
                      <el-option label="智谱 AI (BigModel)" value="zai" />
                      <el-option label="即梦 (Volcengine)" value="jimeng" />
                      <el-option label="MiniMax (海螺)" value="minimax" />
                      <el-option label="ComfyUI (本地/云端)" value="comfyui" />
                      <el-option label="Mock 测试服务" value="mock" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="启用状态">
                    <div class="h-8 flex items-center">
                      <el-switch 
                        v-model="editingProvider.enabled" 
                        active-text="启用" 
                        inactive-text="停用" 
                        inline-prompt
                      />
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="Base URL (可选)">
                <el-input v-model="editingProvider.base_url" placeholder="默认地址，如需代理请修改">
                  <template #prefix><el-icon><Link /></el-icon></template>
                </el-input>
              </el-form-item>

              <el-form-item label="API Key / Token" required>
                <el-input 
                  v-model="editingProvider.api_key" 
                  type="password" 
                  show-password 
                  :placeholder="getKeyPlaceholder(editingProvider.type)"
                />
                <div v-if="editingProvider.type === 'jimeng'" class="text-xs text-orange-500 mt-1">
                  格式：AccessKeyId|SecretKey (用竖线分隔)
                </div>
              </el-form-item>
            </div>

            <!-- 模型列表卡片 -->
            <div class="bg-white border border-gray-200 rounded-lg p-4">
              <div class="flex justify-between items-center mb-4 border-b pb-2">
                <div class="text-sm font-bold text-gray-700 flex items-center gap-2">
                  <el-icon><Cpu /></el-icon> 模型列表
                </div>
                <el-button type="primary" link size="small" icon="Plus" @click="addModel">添加模型</el-button>
              </div>

              <div v-if="editingProvider.models && editingProvider.models.length > 0" class="space-y-3">
                <div v-for="(m, idx) in editingProvider.models" :key="idx" class="flex gap-2 items-center group">
                  <el-input v-model="m.name" placeholder="模型名 (如: qwen-max)" class="flex-[2]" />
                  <el-select v-model="m.type" placeholder="能力类型" class="flex-[1]" style="min-width: 100px;">
                    <el-option label="文本 (Text)" value="text" />
                    <el-option label="图片 (Image)" value="image" />
                    <el-option label="视频 (Video)" value="video" />
                    <el-option label="融图 (Fusion)" value="image_fusion" />
                    <el-option label="语音 (Audio)" value="audio" />
                  </el-select>
                  <el-input v-model="m.path" placeholder="自定义 Path (选填)" class="flex-[1]" />
                  <el-button 
                    type="danger" 
                    link 
                    icon="Delete" 
                    class="opacity-0 group-hover:opacity-100 transition-opacity" 
                    @click="removeModel(idx)" 
                  />
                </div>
              </div>
              <el-empty v-else description="暂无模型，请点击添加" :image-size="60" />
            </div>

          </el-form>
        </div>

        <!-- 底部操作栏 -->
        <div v-if="editingProvider" class="p-4 border-t bg-gray-50 flex justify-between items-center">
          <el-popconfirm 
            v-if="editingProvider.id" 
            title="确定删除此供应商配置吗?" 
            confirm-button-type="danger"
            @confirm="deleteCurrentProvider"
          >
            <template #reference>
              <el-button type="danger" plain icon="Delete">删除</el-button>
            </template>
          </el-popconfirm>
          <div v-else></div> <!-- 占位 -->

          <el-button type="primary" plain size="large" icon="Check" :loading="saving" @click="saveCurrentProvider" class="px-8">
            保存配置
          </el-button>
        </div>
        
        <!-- 空状态 -->
        <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-400">
          <el-icon size="64" class="mb-4 text-gray-200"><Service /></el-icon>
          <p>请在左侧选择或新建一个供应商</p>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import request from '@/api' // 使用封装好的 axios
import { ElMessage } from 'element-plus'

const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// State
const providers = ref([])
const editingProvider = ref(null)
const saving = ref(false)

// Colors mapping
const getProviderColor = (type) => {
  const map = {
    aliyun: '#FF6A00',
    siliconflow: '#7B68EE',
    vidu: '#FF1493',
    zai: '#5683EE',
    jimeng: '#FF4500',
    comfyui: '#3CB371',
    minimax: '#FFD700',
    mock: '#909399'
  }
  return map[type] || '#409EFF'
}

const getKeyPlaceholder = (type) => {
  if (type === 'jimeng') return 'AccessKeyId|SecretKey'
  return '请输入 API Key (不修改请留空)'
}

// Actions
const fetchSettings = async () => {
  try {
    const res = await request.get('/settings')
    providers.value = res || []
    // 如果没有选中的，默认不选；或者可以默认选第一个
    if (providers.value.length > 0 && !editingProvider.value) {
      // 可以在这里逻辑决定是否默认选中第一个，目前保持空状态让用户选
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载配置失败')
  }
}

const initNewProvider = () => {
  editingProvider.value = {
    id: '',
    name: 'New Provider',
    type: 'aliyun',
    base_url: '',
    api_key: '',
    enabled: true,
    models: [
      { name: 'qwen-max', type: 'text', path: '' },
      { name: 'wanx-v1', type: 'image', path: '' }
    ]
  }
}

const selectProvider = (p) => {
  // Deep copy to avoid modifying list directly before save
  editingProvider.value = JSON.parse(JSON.stringify(p))
}

const addModel = () => {
  if (!editingProvider.value.models) editingProvider.value.models = []
  editingProvider.value.models.push({ name: '', type: 'text', path: '' })
}

const removeModel = (idx) => {
  editingProvider.value.models.splice(idx, 1)
}

const handleTypeChange = (val) => {
  // 切换类型时，自动填充一些默认模型名称作为提示
  if (val === 'aliyun') {
    editingProvider.value.models = [
        { name: 'qwen-max', type: 'text' }, 
        { name: 'wanx-v1', type: 'image' }
    ]
  } else if (val === 'siliconflow') {
    editingProvider.value.models = [
        { name: 'Qwen/Qwen2.5-7B-Instruct', type: 'text' },
        { name: 'black-forest-labs/FLUX.1-schnell', type: 'image' }
    ]
  }
}

const saveCurrentProvider = async () => {
  if (!editingProvider.value.name) return ElMessage.warning('请输入供应商名称')
  
  saving.value = true
  try {
    const res = await request.post('/settings/provider', editingProvider.value)
    if (res.success) {
      ElMessage.success('保存成功')
      await fetchSettings()
      // 重新选中刚才保存的（有了ID）
      const savedId = editingProvider.value.id || res.id
      const match = providers.value.find(p => p.id === savedId)
      if (match) selectProvider(match)
    }
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

const deleteCurrentProvider = async () => {
  if (!editingProvider.value.id) return
  try {
    await request.delete(`/settings/provider/${editingProvider.value.id}`)
    ElMessage.success('已删除')
    editingProvider.value = null
    fetchSettings()
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped>
/* 隐藏滚动条但保留滚动功能（兼容性写法） */
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