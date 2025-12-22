<template>
  <div class="shot-list-tab h-full flex flex-col bg-gray-50">
    <!-- 顶部工具栏 -->
    <div class="bg-white px-6 py-3 border-b border-gray-200 flex justify-between items-center shadow-sm z-10 shrink-0">
      <div class="flex items-center gap-4">
        <span class="text-base font-bold text-gray-700">分镜清单</span>
        <el-tag type="info" effect="plain" round size="small">{{ store.shotList.length }} 镜头</el-tag>
      </div>
      
      <div class="flex gap-3">
        <el-button type="primary" size="small" :icon="Plus" @click="openCreateDialog">新建分镜</el-button>
        <el-button type="primary" plain size="small" :icon="Upload" @click="triggerImport">导入 Excel</el-button>
        <el-button type="warning" plain size="small" :icon="Download" @click="exportData">导出 JSON</el-button>
        <el-button circle size="small" :icon="Refresh" @click="refreshList" />
      </div>
    </div>

    <!-- 自定义表头 -->
    <div class="grid grid-cols-[80px_1fr_200px_120px] gap-4 px-6 py-2 bg-gray-100/80 text-xs font-medium text-gray-500 border-b border-gray-200 shrink-0 select-none">
      <div class="text-center">场次-镜号</div>
      <div class="pl-2">画面与声音内容</div>
      <div>技术参数</div>
      <div class="text-right pr-2">角色 & 时长</div>
    </div>

    <!-- 分镜列表区域 -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
      <div 
        v-for="(item, index) in store.shotList" 
        :key="item.id" 
        class="shot-card group relative"
      >
        <!-- 1. 索引区块 -->
        <div class="index-section">
          <div class="scene-badge">
            <span class="label">场</span>
            <span class="value">{{ item.scene }}</span>
          </div>
          <div class="divider-vertical"></div>
          <div class="shot-badge">
            <span class="label">镜</span>
            <span class="value">{{ item.shot_number }}</span>
          </div>
        </div>

        <!-- 2. 内容详情区块 -->
        <div class="content-section">
          <!-- 画面描述 -->
          <div class="content-row">
            <el-icon class="icon visual"><VideoCamera /></el-icon>
            <div class="text-content">
              <span class="label">画面：</span>
              <span class="text-gray-800">{{ item.visual_description || item.scene_description || '暂无画面描述' }}</span>
            </div>
          </div>
          <!-- 虚线分割 -->
          <div class="border-t border-dashed border-gray-100 my-2"></div>
          <!-- 声音/台词 -->
          <div class="content-row">
            <el-icon class="icon audio"><Microphone /></el-icon>
            <div class="text-content">
              <span class="label">声音：</span>
              <span class="text-gray-600" v-if="item.dialogue || item.audio_description">
                <span v-if="item.dialogue" class="text-blue-600 mr-2">“{{ item.dialogue }}”</span>
                <span v-if="item.audio_description" class="italic text-gray-400">({{ item.audio_description }})</span>
              </span>
              <span v-else class="text-gray-300 italic">无对白/音效</span>
            </div>
          </div>
        </div>

        <!-- 3. 技术参数区块 -->
        <div class="tech-section">
          <div class="tech-grid">
            <div class="tech-item" title="景别">
              <span class="tech-label">景别</span>
              <span class="tech-value">{{ item.shot_size || '-' }}</span>
            </div>
            <div class="tech-item" title="运镜">
              <span class="tech-label">运镜</span>
              <span class="tech-value">{{ item.camera_movement || '-' }}</span>
            </div>
            <div class="tech-item" title="角度">
              <span class="tech-label">角度</span>
              <span class="tech-value">{{ item.camera_angle || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- 4. 角色与元数据区块 -->
        <div class="meta-section">
          <div class="characters">
            <el-tag 
              v-for="charName in getCharNameList(item.characters)" 
              :key="charName"
              size="small" 
              type="info" 
              effect="plain"
              class="mb-1 mr-1"
            >
              {{ charName }}
            </el-tag>
            <span v-if="!item.characters?.length" class="text-xs text-gray-300">-</span>
          </div>
          <div class="duration">
            <el-icon><Timer /></el-icon>
            <span>{{ item.duration ? item.duration + 's' : '-' }}</span>
          </div>
        </div>

        <!-- 悬浮操作栏 -->
        <div class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 bg-white/90 p-1 rounded shadow-sm border border-gray-100 backdrop-blur-sm z-10">
           <el-tooltip content="编辑" placement="top">
             <el-button type="primary" circle size="small" :icon="Edit" @click.stop="openEditDialog(item)" />
           </el-tooltip>
           <el-tooltip content="向下插入" placement="top">
             <el-button type="success" circle size="small" :icon="Plus" @click.stop="insertShot(index)" />
           </el-tooltip>
           <el-tooltip content="删除" placement="top">
             <el-button type="danger" circle size="small" :icon="Delete" @click.stop="handleDelete(item)" />
           </el-tooltip>
        </div>
      </div>

      <el-empty v-if="store.shotList.length === 0" description="暂无分镜数据，请导入或创建" />
    </div>

    <!-- 编辑/新建弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="editingId ? '编辑分镜' : (insertIndex > -1 ? '插入分镜' : '新建分镜')" 
      width="600px" 
      destroy-on-close
    >
      <el-form :model="form" label-width="90px">
        <div class="flex gap-4">
          <el-form-item label="场次" required class="flex-1">
            <el-input v-model="form.scene" placeholder="例如: 1" />
          </el-form-item>
          <el-form-item label="镜号" required class="flex-1">
            <el-input v-model="form.shot_number" placeholder="例如: 1" />
          </el-form-item>
        </div>

        <el-form-item label="画面描述">
          <el-input v-model="form.visual_description" type="textarea" :rows="3" placeholder="画面中发生了什么..." />
        </el-form-item>

        <el-form-item label="台词">
          <el-input v-model="form.dialogue" type="textarea" :rows="2" placeholder="角色对白..." />
        </el-form-item>

        <el-form-item label="声音/音效">
          <el-input v-model="form.audio_description" placeholder="背景音、音效..." />
        </el-form-item>

        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="景别">
            <el-select v-model="form.shot_size" placeholder="选择或输入" allow-create filterable>
               <el-option label="远景" value="远景" />
               <el-option label="全景" value="全景" />
               <el-option label="中景" value="中景" />
               <el-option label="近景" value="近景" />
               <el-option label="特写" value="特写" />
            </el-select>
          </el-form-item>
          <el-form-item label="运镜">
             <el-input v-model="form.camera_movement" placeholder="推/拉/摇/移..." />
          </el-form-item>
          <el-form-item label="角度">
             <el-input v-model="form.camera_angle" placeholder="平视/俯视/仰视..." />
          </el-form-item>
          <el-form-item label="时长(s)">
             <el-input-number v-model="form.duration" :min="0" :step="0.5" class="!w-full" />
          </el-form-item>
        </div>

        <el-form-item label="涉及角色">
          <el-select 
            v-model="form.characters" 
            multiple 
            placeholder="选择角色" 
            class="w-full"
          >
            <el-option 
              v-for="char in store.characterList" 
              :key="char.id" 
              :label="char.name" 
              :value="char.id" 
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 隐藏的文件输入框 -->
    <input 
      type="file" 
      ref="importInput" 
      class="hidden" 
      accept=".xlsx, .xls" 
      @change="handleImportFile" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { getShots, batchCreateShots, createShot, updateShot, deleteShot } from '@/api/project'
import { Refresh, Download, Upload, VideoCamera, Microphone, Timer, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { read, utils } from 'xlsx'

const store = useProjectStore()
const importInput = ref(null)

// Dialog & Form State
const dialogVisible = ref(false)
const editingId = ref(null)
const insertIndex = ref(-1)
const form = ref({
  scene: '',
  shot_number: '',
  visual_description: '',
  dialogue: '',
  audio_description: '',
  shot_size: '',
  camera_movement: '',
  camera_angle: '',
  duration: 0,
  characters: []
})

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

// 辅助函数：获取角色名数组
const getCharNameList = (chars) => {
  if (!chars) return []
  if (typeof chars[0] === 'object') {
    return chars.map(c => c.name)
  }
  return store.characterList
    .filter(c => chars.includes(c.id))
    .map(c => c.name)
}

// 辅助函数：将 ID 数组转换为对象数组 (供前端展示更新)
const getCharacterObjects = (ids) => {
  if (!ids || ids.length === 0) return []
  return store.characterList.filter(c => ids.includes(c.id))
}

// --- CRUD Operations ---

const resetForm = () => {
  form.value = {
    scene: '',
    shot_number: '',
    visual_description: '',
    dialogue: '',
    audio_description: '',
    shot_size: '',
    camera_movement: '',
    camera_angle: '',
    duration: 0,
    characters: []
  }
}

const openCreateDialog = () => {
  editingId.value = null
  insertIndex.value = -1
  resetForm()
  // 自动填充上一条的场次和镜号+1
  if (store.shotList.length > 0) {
    const last = store.shotList[store.shotList.length - 1]
    form.value.scene = last.scene
    const num = parseInt(last.shot_number)
    if (!isNaN(num)) form.value.shot_number = String(num + 1)
  }
  dialogVisible.value = true
}

const openEditDialog = (item) => {
  editingId.value = item.id
  insertIndex.value = -1
  // 深拷贝并处理角色字段
  const copy = JSON.parse(JSON.stringify(item))
  // 将 visual_description 映射回表单 (如果 API 字段名不一致)
  if (!copy.visual_description && copy.scene_description) {
    copy.visual_description = copy.scene_description
  }
  // 提取角色 ID
  if (copy.characters && copy.characters.length > 0 && typeof copy.characters[0] === 'object') {
    copy.characters = copy.characters.map(c => c.id)
  } else if (!copy.characters) {
    copy.characters = []
  }
  form.value = copy
  dialogVisible.value = true
}

const insertShot = (index) => {
  editingId.value = null
  insertIndex.value = index + 1
  resetForm()
  // 智能填充
  const prev = store.shotList[index]
  if (prev) {
    form.value.scene = prev.scene
    const num = parseInt(prev.shot_number)
    if (!isNaN(num)) form.value.shot_number = String(num + 1)
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.value.scene || !form.value.shot_number) {
    return ElMessage.warning('场次和镜号必填')
  }

  // 构造 payload，映射回后端字段
  const payload = {
    ...form.value,
    scene_description: form.value.visual_description, // 兼容后端可能使用的字段
    movie_id: store.currentProjectId
  }

  try {
    if (editingId.value) {
      // 编辑
      const res = await updateShot(store.currentProjectId, editingId.value, payload)
      // 更新本地列表
      const idx = store.shotList.findIndex(s => s.id === editingId.value)
      if (idx !== -1) {
        // 补充角色对象用于显示
        res.characters = getCharacterObjects(payload.characters)
        // 确保 visual_description 存在
        res.visual_description = payload.visual_description
        store.shotList[idx] = res
      }
      ElMessage.success('更新成功')
    } else {
      // 新增 / 插入
      if (insertIndex.value > -1) {
        payload.insert_index = insertIndex.value
      }
      const res = await createShot(store.currentProjectId, payload)
      // 补充角色对象
      res.characters = getCharacterObjects(payload.characters)
      res.visual_description = payload.visual_description
      
      if (insertIndex.value > -1) {
        store.shotList.splice(insertIndex.value, 0, res)
      } else {
        store.shotList.push(res)
      }
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
  } catch (e) {
    console.error(e)
    ElMessage.error('保存失败')
  }
}

const handleDelete = async (item) => {
  try {
    await ElMessageBox.confirm('确定删除该分镜吗?', '提示', { type: 'warning' })
    await deleteShot(store.currentProjectId, item.id)
    store.shotList = store.shotList.filter(s => s.id !== item.id)
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

// --- Import/Export ---

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
      const data = new Uint8Array(event.target.result)
      const workbook = read(data, { type: 'array' })
      const firstSheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[firstSheetName]
      const jsonData = utils.sheet_to_json(worksheet)

      if (!jsonData || jsonData.length === 0) return ElMessage.warning('Excel 文件为空')

      const validShots = jsonData.map(row => {
        const getValue = (keys) => {
          for (const key of keys) if (row[key] != null) return String(row[key]).trim()
          return ''
        }
        return {
          scene: getValue(['场次', 'scene', 'Scene', '场']),
          shot_number: getValue(['镜号', 'shot_number', 'Shot', '号']),
          visual_description: getValue(['画面内容', '画面描述', 'visual_description', 'Visual', '画面']),
          dialogue: getValue(['台词', 'dialogue', 'Dialogue']),
          audio_description: getValue(['声音', '音效', 'audio_description', 'Audio']),
          shot_size: getValue(['景别', 'shot_size', 'Size']),
          camera_movement: getValue(['运镜', 'camera_movement', 'Movement']),
          camera_angle: getValue(['角度', 'camera_angle', 'Angle']),
          duration: getValue(['时长', 'duration', 'Duration']),
          movie_id: store.currentProjectId
        }
      }).filter(item => item.scene || item.shot_number)

      if (validShots.length === 0) return ElMessage.warning('无有效数据')

      await ElMessageBox.confirm(`解析到 ${validShots.length} 条数据，确定导入吗？`, '确认', { type: 'info' })
      
      store.loading.shots = true
      try {
        await batchCreateShots(store.currentProjectId, validShots)
        ElMessage.success(`导入成功`)
        refreshList()
      } catch (err) {
        console.error(err)
        ElMessage.error('导入失败')
      } finally {
        store.loading.shots = false
      }
    } catch (err) {
      ElMessage.error('解析失败')
    }
  }
  reader.readAsArrayBuffer(file)
}
</script>

<style scoped>
/* 卡片基础样式 */
.shot-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  display: grid;
  grid-template-columns: 80px 1fr 200px 120px; /* 定义四列布局 */
  gap: 16px;
  padding: 0; /* padding 由子元素控制以实现分割线效果 */
  transition: all 0.2s ease;
  position: relative;
  min-height: 100px;
}

.shot-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: #d1d5db;
  transform: translateY(-1px);
}

/* 1. 索引区 */
.index-section {
  background-color: #f9fafb;
  border-right: 1px solid #f3f4f6;
  border-top-left-radius: 8px;
  border-bottom-left-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 0;
}

.scene-badge, .shot-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.label {
  font-size: 10px;
  color: #9ca3af;
  text-transform: uppercase;
}

.value {
  font-size: 18px;
  font-weight: 800;
  color: #374151;
  line-height: 1.2;
}

.divider-vertical {
  width: 20px;
  height: 1px;
  background-color: #e5e7eb;
  margin: 6px 0;
}

/* 2. 内容区 */
.content-section {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.content-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.icon {
  margin-top: 3px;
  font-size: 14px;
}
.icon.visual { color: #8b5cf6; } /* 紫色眼睛 */
.icon.audio { color: #f59e0b; }  /* 橙色麦克风 */

.text-content {
  font-size: 13px;
  line-height: 1.5;
  color: #1f2937;
}

.text-content .label {
  color: #9ca3af;
  margin-right: 4px;
}

/* 3. 技术参数区 */
.tech-section {
  padding: 16px 0;
  display: flex;
  align-items: center;
  border-left: 1px dashed #f3f4f6;
  padding-left: 16px;
}

.tech-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
}

.tech-item {
  background-color: #f3f4f6;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  display: flex;
  flex-direction: column;
}

.tech-item:last-child {
  grid-column: span 2; /* 让最后一个元素占满一行 */
}

.tech-label {
  color: #9ca3af;
  font-size: 9px;
  margin-bottom: 2px;
}

.tech-value {
  font-weight: 600;
  color: #4b5563;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 4. 元数据区 */
.meta-section {
  padding: 16px 16px 16px 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 8px;
}

.characters {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 100%;
}

.duration {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}

.hidden { display: none; }

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