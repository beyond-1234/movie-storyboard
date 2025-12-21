<template>
  <div class="script-tab h-full flex flex-col">
    <!-- 顶部工具栏 -->
    <div class="bg-white p-3 rounded shadow-sm mb-4 flex justify-between items-center sticky top-0 z-10">
      <div class="flex items-center gap-4">
        <div class="flex items-center">
          <el-checkbox 
            v-model="checkAll" 
            :indeterminate="isIndeterminate" 
            @change="handleCheckAllChange"
          >
            全选
          </el-checkbox>
          <span class="ml-3 text-xs text-gray-500">已选 {{ selectedCount }} 项</span>
        </div>
        
        <div class="w-px h-6 bg-gray-200 mx-2"></div>
        
        <ModelSelector 
          type="text" 
          label="AI 模型" 
          v-model:provider="store.genOptions.textProviderId" 
          v-model:model="store.genOptions.textModelName" 
        />
        <span class="text-xs text-gray-400 hidden lg:inline-block">建议使用参数量较大的模型 (如 Qwen-Max, GPT-4) 以获得最佳分析效果</span>
      </div>

      <div class="flex gap-2">
        <el-popconfirm title="确定删除选中的段落吗?" @confirm="deleteSelected">
          <template #reference>
            <el-button type="danger" plain size="small" icon="Delete" :disabled="selectedCount === 0">批量删除</el-button>
          </template>
        </el-popconfirm>
        
        <el-popconfirm title="确定清空所有剧本吗? 此操作不可恢复。" @confirm="clearAll">
          <template #reference>
            <el-button type="danger" plain size="small" icon="DeleteFilled" :disabled="scriptList.length === 0">清空全部</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <!-- 剧本列表区域 -->
    <div class="flex-1 overflow-y-auto pr-2" ref="scrollContainer">
      <div ref="sortableListRef" class="space-y-4 pb-4">
        <div 
          v-for="(section, index) in scriptList" 
          :key="section._localId || index" 
          class="script-section-block bg-white border-l-4 border-blue-500 rounded-r shadow-sm hover:shadow-md transition-shadow p-4 flex gap-4 group"
        >
          <!-- 选择框 -->
          <div class="pt-2">
            <el-checkbox v-model="section._checked" @change="handleSelectionChange" />
          </div>

          <!-- 内容主体 -->
          <div class="flex-1 min-w-0">
            <div class="flex justify-between items-start mb-2">
              <span class="text-xs font-bold text-gray-300 select-none">#{{ index + 1 }}</span>
              <!-- 拖拽手柄 -->
              <el-icon class="cursor-move text-gray-300 hover:text-gray-600 handle"><Rank /></el-icon>
            </div>

            <el-input 
              v-model="section.content" 
              type="textarea" 
              :autosize="{ minRows: 3, maxRows: 15 }" 
              placeholder="请输入剧本内容..." 
              class="script-textarea"
              @change="saveData"
            />
            
            <!-- 单行工具栏 (Hover 显示) -->
            <div class="flex justify-end gap-3 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <el-button 
                size="small" 
                type="success" 
                plain 
                icon="MagicStick" 
                :loading="section._loadingContinue"
                @click="handleContinuation(index)"
              >
                AI 续写
              </el-button>
              
              <el-button 
                size="small" 
                type="primary" 
                plain 
                icon="VideoCamera" 
                :loading="section._loadingConvert"
                @click="handleConvertToShot(section)"
              >
                一键转分镜
              </el-button>
              
              <el-button 
                size="small" 
                type="danger" 
                plain 
                icon="Delete" 
                @click="removeSection(index)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 底部添加按钮 -->
      <el-button 
        class="w-full mt-2 border-dashed py-4 text-gray-500 hover:text-blue-500 hover:border-blue-500 transition-colors" 
        icon="Plus" 
        plain
        @click="addSection"
      >
        添加新段落
      </el-button>
      <div class="h-10"></div> <!-- 底部留白 -->
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import Sortable from 'sortablejs'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import ModelSelector from '@/components/ModelSelector.vue'
import { getScript, saveScript, createShot } from '@/api/project'
import { analyzeScript, scriptContinuation } from '@/api/generation'
import { ElMessage, ElNotification } from 'element-plus'

const store = useProjectStore()
const loadingStore = useLoadingStore()

// State
const scriptList = ref([])
const sortableListRef = ref(null)

// Selection State
const checkAll = ref(false)
const isIndeterminate = ref(false)

const selectedCount = computed(() => scriptList.value.filter(s => s._checked).length)

// --- Initialization ---

onMounted(async () => {
  if (store.currentProjectId) {
    await fetchScriptData()
    initSortable()
  }
})

const fetchScriptData = async () => {
  try {
    const res = await getScript(store.currentProjectId)
    // 为每个段落添加前端状态控制字段
    scriptList.value = (res && res.length > 0 ? res : [{ content: '' }]).map(item => ({
      ...item,
      _localId: Math.random().toString(36).substr(2, 9), // 用于 key
      _checked: false,
      _loadingContinue: false,
      _loadingConvert: false
    }))
    updateCheckState()
  } catch (e) {
    console.error(e)
  }
}

const initSortable = () => {
  if (!sortableListRef.value) return
  
  Sortable.create(sortableListRef.value, {
    handle: '.handle',
    animation: 150,
    ghostClass: 'bg-blue-50',
    onEnd: ({ oldIndex, newIndex }) => {
      if (oldIndex === newIndex) return
      // 移动数组元素
      const item = scriptList.value.splice(oldIndex, 1)[0]
      scriptList.value.splice(newIndex, 0, item)
      saveData()
    }
  })
}

// --- Data Persistence ---

const saveData = async () => {
  if (!store.currentProjectId) return
  // 过滤掉前端临时字段再保存
  const cleanData = scriptList.value.map(({ _checked, _localId, _loadingContinue, _loadingConvert, ...rest }) => rest)
  try {
    await saveScript(store.currentProjectId, cleanData)
  } catch (e) {
    console.error('Auto save failed', e)
  }
}

// --- Core Actions ---

const addSection = () => {
  scriptList.value.push({
    content: '',
    _localId: Math.random().toString(36).substr(2, 9),
    _checked: false
  })
  saveData()
  // 自动滚动到底部
  nextTick(() => {
    const container = document.querySelector('.script-tab .overflow-y-auto')
    if (container) container.scrollTop = container.scrollHeight
  })
}

const removeSection = (index) => {
  scriptList.value.splice(index, 1)
  saveData()
  updateCheckState()
}

// --- Batch Actions ---

const handleCheckAllChange = (val) => {
  scriptList.value.forEach(item => item._checked = val)
  isIndeterminate.value = false
}

const handleSelectionChange = () => {
  updateCheckState()
}

const updateCheckState = () => {
  const count = selectedCount.value
  checkAll.value = count > 0 && count === scriptList.value.length
  isIndeterminate.value = count > 0 && count < scriptList.value.length
}

const deleteSelected = () => {
  scriptList.value = scriptList.value.filter(item => !item._checked)
  updateCheckState()
  saveData()
  ElMessage.success('批量删除成功')
}

const clearAll = () => {
  scriptList.value = []
  saveData()
  updateCheckState()
  ElMessage.success('已清空')
}

// --- AI Features ---

// 1. AI 续写
const handleContinuation = async (index) => {
  if (!store.genOptions.textProviderId) return ElMessage.warning('请先选择 AI 模型')
  
  // 获取上下文 (前2段 + 当前段)
  const contextSections = scriptList.value.slice(Math.max(0, index - 2), index + 1)
  const contextText = contextSections.map(s => s.content).join('\n')
  
  if (!contextText.trim()) return ElMessage.warning('请先输入一些内容作为续写依据')

  const targetSection = scriptList.value[index]
  targetSection._loadingContinue = true
  
  try {
    const res = await scriptContinuation({
      context_text: contextText,
      project_info: store.currentProject, // 传入项目背景信息
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })
    
    // 在当前段落后插入新段落
    if (res.content) {
      scriptList.value.splice(index + 1, 0, {
        content: res.content,
        _localId: Math.random().toString(36).substr(2, 9),
        _checked: false
      })
      saveData()
      ElMessage.success('续写完成')
    }
  } catch (e) {
    console.error(e)
  } finally {
    targetSection._loadingContinue = false
  }
}

// 2. 一键转分镜
const handleConvertToShot = async (section) => {
  if (!section.content.trim()) return ElMessage.warning('剧本内容为空')
  if (!store.genOptions.textProviderId) return ElMessage.warning('请先选择 AI 模型')

  section._loadingConvert = true
  // 使用全局遮罩提示，因为这个过程可能较慢且包含多次DB写入
  loadingStore.start('正在拆解分镜', 'AI 正在分析剧本中的动作、台词与镜头语言...')

  try {
    // 1. 调用 AI 分析接口
    const res = await analyzeScript({
      content: section.content,
      project_id: store.currentProjectId,
      provider_id: store.genOptions.textProviderId,
      model_name: store.genOptions.textModelName
    })

    if (res.shots && res.shots.length > 0) {
      // 2. 循环创建分镜 (调用后端 Shot API)
      let count = 0
      for (const shotData of res.shots) {
        // 简单处理角色字段：如果是字符串数组，后端API通常需要处理
        // 假设 analyze_script 返回的格式与 createShot 兼容
        // 补全 movie_id
        await createShot(store.currentProjectId, {
          ...shotData,
          movie_id: store.currentProjectId
        })
        count++
      }
      
      ElNotification({
        title: '转换成功',
        message: `已将该段剧本拆解为 ${count} 个分镜，请前往“场景列表”查看`,
        type: 'success',
        duration: 5000
      })
    } else {
      ElMessage.warning('AI 未能识别出有效的分镜信息')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('转换失败，请重试')
  } finally {
    section._loadingConvert = false
    loadingStore.stop()
  }
}
</script>

<style scoped>
/* 可以在这里覆盖 el-textarea 的样式使其更像剧本编辑器 */
.script-textarea :deep(.el-textarea__inner) {
  border: none;
  background-color: transparent;
  padding: 0;
  font-size: 15px;
  line-height: 1.6;
  color: #333;
  box-shadow: none; /* 移除 Element Plus 默认的 focus shadow */
}

.script-textarea :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

/* 选中状态的样式 */
.script-section-block:has(.el-checkbox.is-checked) {
  background-color: #f0f9eb;
  border-color: #67c23a;
}
</style>