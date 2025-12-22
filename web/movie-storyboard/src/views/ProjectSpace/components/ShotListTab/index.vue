<template>
  <div class="shot-list-tab h-full flex flex-col">
    <!-- 顶部工具栏 -->
    <div class="bg-white p-3 rounded shadow-sm mb-4 flex justify-between items-center">
      <div class="flex items-center gap-4">
        <span class="text-sm text-gray-500">共 {{ store.shotList.length }} 个分镜</span>
      </div>
      
      <div class="flex gap-2">
        <el-button type="primary" size="small" icon="Upload" @click="triggerImport">导入 JSON</el-button>
        <el-button type="info" plain size="small" icon="Download" @click="exportData">导出 JSON</el-button>
        <el-button type="default" size="small" icon="Refresh" @click="refreshList">刷新</el-button>
      </div>
    </div>

    <!-- 纯数据表格 -->
    <el-table 
      :data="store.shotList" 
      v-loading="store.loading.shots" 
      border 
      stripe 
      height="100%"
      class="flex-1"
      size="small"
    >
      <el-table-column prop="scene" label="场次" width="60" align="center" sortable />
      <el-table-column prop="shot_number" label="镜号" width="60" align="center" sortable />
      
      <!-- 拍摄参数 -->
      <el-table-column prop="shot_size" label="景别" width="80" align="center" show-overflow-tooltip />
      <el-table-column prop="camera_movement" label="运镜" width="80" align="center" show-overflow-tooltip />
      <el-table-column prop="camera_angle" label="角度" width="80" align="center" show-overflow-tooltip />

      <!-- 内容描述 -->
      <el-table-column label="画面内容 (Visual)" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.visual_description || row.scene_description }}
        </template>
      </el-table-column>
      
      <el-table-column prop="dialogue" label="台词 (Dialogue)" min-width="150" show-overflow-tooltip />
      <el-table-column prop="audio_description" label="声音/音效 (Audio)" min-width="150" show-overflow-tooltip />
      
      <!-- 其它信息 -->
      <el-table-column label="角色" width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.characters && row.characters.length">
             {{ getCharNames(row.characters) }}
          </span>
          <span v-else class="text-gray-300">-</span>
        </template>
      </el-table-column>
      
      <el-table-column prop="duration" label="时长(s)" width="70" align="center" />
    </el-table>

    <!-- 隐藏的文件输入框 -->
    <input 
      type="file" 
      ref="importInput" 
      class="hidden" 
      accept=".json" 
      @change="handleImportFile" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { getShots, batchCreateShots } from '@/api/project'
import { Refresh, Download, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useProjectStore()
const importInput = ref(null)

onMounted(() => {
  if (store.currentProjectId) {
    refreshList()
  }
})

const refreshList = async () => {
  store.loading.shots = true
  try {
    const res = await getShots(store.currentProjectId)
    store.shotList = res || []
  } finally {
    store.loading.shots = false
  }
}

const getCharNames = (chars) => {
  if (!chars) return ''
  // 兼容对象数组或ID数组
  if (typeof chars[0] === 'object') {
    return chars.map(c => c.name).join(', ')
  }
  // 如果是ID，去 store 查找
  return store.characterList
    .filter(c => chars.includes(c.id))
    .map(c => c.name)
    .join(', ')
}

const exportData = () => {
  if (store.shotList.length === 0) return ElMessage.warning('没有数据可导出')
  const dataStr = JSON.stringify(store.shotList, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `shots_${store.currentProjectId}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  ElMessage.success('导出成功')
}

// --- 导入功能 ---

const triggerImport = () => {
  importInput.value.value = ''
  importInput.value.click()
}

const handleImportFile = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = async (event) => {
    try {
      const jsonContent = JSON.parse(event.target.result)
      
      if (!Array.isArray(jsonContent)) {
        return ElMessage.error('导入文件格式错误：必须是 JSON 数组')
      }

      // 简单的数据清洗/验证
      const validShots = jsonContent.map(item => ({
        // 确保必要的字段存在，或者设为默认值
        scene: item.scene || '',
        shot_number: item.shot_number || '',
        visual_description: item.visual_description || item.scene_description || '',
        dialogue: item.dialogue || '',
        audio_description: item.audio_description || '',
        shot_size: item.shot_size || '',
        camera_movement: item.camera_movement || '',
        camera_angle: item.camera_angle || '',
        duration: item.duration || '',
        movie_id: store.currentProjectId // 强制关联当前项目
      }))

      if (validShots.length === 0) {
        return ElMessage.warning('文件中没有有效的分镜数据')
      }

      await ElMessageBox.confirm(
        `解析到 ${validShots.length} 条分镜数据，确定导入吗？`, 
        '确认导入', 
        { type: 'info' }
      )

      // 调用批量创建接口
      store.loading.shots = true
      try {
        await batchCreateShots(store.currentProjectId, validShots)
        ElMessage.success(`成功导入 ${validShots.length} 条数据`)
        refreshList() // 刷新列表
      } catch (err) {
        console.error(err)
      } finally {
        store.loading.shots = false
      }

    } catch (err) {
      console.error(err)
      ElMessage.error('解析文件失败：请确保是有效的 JSON 文件')
    }
  }
  reader.readAsText(file)
}
</script>

<style scoped>
.hidden {
  display: none;
}
</style>