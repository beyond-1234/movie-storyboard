<template>
  <div class="shot-list-tab h-full flex flex-col bg-gray-50">
    <!-- 顶部工具栏 -->
    <div class="bg-white px-6 py-3 border-b border-gray-200 flex justify-between items-center shadow-sm z-10 shrink-0">
      <div class="flex items-center gap-4">
        <!-- 全选 -->
        <el-checkbox 
          v-model="isAllSelected" 
          :indeterminate="isIndeterminate" 
          @change="handleSelectAllChange"
        >
          全选
        </el-checkbox>
        
        <div class="w-px h-6 bg-gray-200 mx-2"></div>

        <!-- 模型配置 -->
        <ModelSelector 
          type="text" 
          label="文本" 
          v-model:provider="store.genOptions.textProviderId" 
          v-model:model="store.genOptions.textModelName" 
        />
        <ModelSelector 
          type="image" 
          label="生图" 
          v-model:provider="store.genOptions.imageProviderId" 
          v-model:model="store.genOptions.imageModelName" 
        />
      </div>
      
      <div class="flex gap-2 items-center">
        <!-- 批量 AI 菜单 -->
        <el-dropdown split-button type="success" size="small" @click="handleBatchAI('full')" @command="handleBatchAI">
          <el-icon class="mr-1"><MagicStick /></el-icon> 批量一键生成
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="prompt">批量生成提示词</el-dropdown-item>
              <el-dropdown-item command="image">批量生成场景图</el-dropdown-item>
              <el-dropdown-item command="full" divided>智能链式生成 (词+图)</el-dropdown-item>
              <el-dropdown-item command="fusion" divided>批量同步至融图任务</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <div class="w-px h-4 bg-gray-200 mx-1"></div>

        <el-button type="danger" plain size="small" :icon="Delete" :disabled="selectedIds.length === 0" @click="handleBatchDelete">删除选中</el-button>
        <el-button type="primary" size="small" :icon="Plus" @click="openCreateDialog">新建</el-button>
        <el-button type="primary" plain size="small" :icon="Upload" @click="triggerImport">导入</el-button>
        <el-button circle size="small" :icon="Refresh" @click="refreshList" />
      </div>
    </div>

    <!-- 表头 (调整列宽以容纳角色头像和预览区) -->
    <div class="grid grid-cols-[80px_1fr_220px_360px] gap-4 px-6 py-2 bg-gray-100/80 text-xs font-medium text-gray-500 border-b border-gray-200 shrink-0 select-none">
      <div class="text-center pl-4">场-镜</div>
      <div class="pl-2">画面与声音内容</div>
      <div class="text-right">出席角色与参数</div>
      <div class="pl-2">生成预览 (场景 / 融图)</div>
    </div>

    <!-- 分镜列表 -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
      <div 
        v-for="(item, index) in displayList" 
        :key="item.id" 
        class="shot-card group relative transition-all duration-200"
        :class="{ 'ring-2 ring-blue-400 bg-blue-50/30': selectedIds.includes(item.id) }"
        @click="toggleSelection(item.id)"
      >
        <!-- 1. 索引区 -->
        <div class="index-section" @click.stop>
          <el-checkbox 
            class="mb-2"
            :model-value="selectedIds.includes(item.id)" 
            @change="toggleSelection(item.id)" 
          />
          <div class="scene-badge">
            <span class="label">场</span>
            <span class="value">{{ item.scene }}</span>
          </div>
          <div class="divider-vertical"></div>
          <div class="shot-badge">
            <span class="label">镜</span>
            <span class="value">{{ item._auto_shot_number }}</span>
          </div>
        </div>

        <!-- 2. 内容区 -->
        <div class="content-section">
          <div class="content-row">
            <el-icon class="icon visual"><VideoCamera /></el-icon>
            <div class="text-content">
              <span class="text-gray-800 font-medium leading-relaxed">{{ item.visual_description || item.scene_description || '暂无画面描述' }}</span>
            </div>
          </div>
          <div class="border-t border-dashed border-gray-100 my-2"></div>
          <div class="content-row">
            <el-icon class="icon audio"><Microphone /></el-icon>
            <div class="text-content">
              <span v-if="item.dialogue" class="text-blue-600 mr-2 font-bold">“{{ item.dialogue }}”</span>
              <span v-if="item.audio_description" class="italic text-gray-400 text-xs">({{ item.audio_description }})</span>
              <span v-if="!item.dialogue && !item.audio_description" class="text-gray-300 italic text-xs">无对白/音效</span>
            </div>
          </div>
        </div>

        <!-- 3. 参数与角色区 (升级为头像卡片样式) -->
        <div class="meta-section">
          <div class="flex flex-wrap gap-1 mb-3 justify-end">
            <el-tag v-if="item.shot_size" size="small" effect="plain" type="info">{{ item.shot_size }}</el-tag>
            <el-tag v-if="item.duration" size="small" effect="plain" type="warning">{{ item.duration }}s</el-tag>
          </div>
          
          <div class="characters-container flex flex-wrap justify-end gap-x-2 gap-y-4 content-start">
            <template v-if="item.characters && item.characters.length > 0">
              <div 
                v-for="char in getCharacterObjects(item.characters)" 
                :key="char.id" 
                class="relative group/char"
              >
                <!-- 人物头像 -->
                <UnifiedImageCard
                  :src="char.image_url"
                  width="42px"
                  height="42px"
                  fit="cover"
                  :placeholder="char.name ? char.name.charAt(0) : '?'"
                  :enable-generate="false"
                  :enable-upload="false"
                  :enable-delete="false"
                  custom-class="border-gray-200 rounded shadow-sm"
                />
                <!-- 悬浮或底部名称 -->
                <div class="absolute -bottom-3.5 left-0 w-full text-center text-[9px] text-gray-500 truncate scale-90 select-none px-0.5" :title="char.name">
                  {{ char.name }}
                </div>
              </div>
            </template>
            <span v-else class="text-[10px] text-gray-300 italic mr-1">无角色信息</span>
          </div>
        </div>

        <!-- 4. 增强预览区 (场景 + 融图) -->
        <div class="preview-section" @click.stop>
          <div class="grid grid-cols-2 gap-3 h-full">
            <!-- 场景卡预览 -->
            <div class="preview-box">
              <span class="preview-label">场景图预览</span>
              <UnifiedImageCard
                :src="item.scene_image"
                width="100%"
                height="100px"
                fit="cover"
                placeholder="点击生成"
                :enable-delete="false"
                @generate="handleOneGen('scene', item)"
              >
                <template #info v-if="item.scene_prompt">Prompt 已就绪</template>
              </UnifiedImageCard>
            </div>

            <!-- 融图预览 (从 store.fusionList 自动匹配) -->
            <div class="preview-box">
              <span class="preview-label">融图/视频预览</span>
              <div v-if="getRelatedFusion(item.id)" class="w-full h-[100px] relative rounded border overflow-hidden">
                <UnifiedImageCard
                   v-if="!getRelatedFusion(item.id).video_url"
                  :src="getRelatedFusion(item.id).result_image"
                  width="100%"
                  height="100%"
                  placeholder="融图中..."
                  :enable-generate="false"
                  :enable-upload="false"
                  :enable-delete="false"
                />
                <div v-else class="w-full h-full bg-black flex items-center justify-center cursor-pointer" @click="playVideo(getRelatedFusion(item.id).video_url)">
                   <video :src="getRelatedFusion(item.id).video_url" class="w-full h-full object-cover opacity-60"></video>
                   <el-icon class="absolute text-white text-3xl"><VideoPlay /></el-icon>
                </div>
              </div>
              <div v-else class="w-full h-[100px] bg-gray-50 border border-dashed rounded flex flex-col items-center justify-center text-gray-300 text-[10px]">
                 <el-icon><CopyDocument /></el-icon>
                 <span class="mt-1">未同步至融图</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 悬浮操作栏 -->
        <div class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 bg-white/90 p-1 rounded shadow-sm border border-gray-100 backdrop-blur-sm z-10" @click.stop>
           <el-tooltip content="编辑详情" placement="top">
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

      <el-empty v-if="store.shotList.length === 0" description="暂无分镜数据" />
    </div>

    <!-- 弹窗部分 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑分镜' : '新建分镜'" width="650px" destroy-on-close>
        <el-form :model="form" label-width="90px">
          <div class="flex gap-4">
            <el-form-item label="场次" required class="flex-1"><el-input v-model="form.scene" placeholder="例如: 1" /></el-form-item>
            <el-form-item label="镜号" class="flex-1"><el-input disabled placeholder="自动生成" /></el-form-item>
          </div>
          <el-form-item label="画面描述">
            <el-input v-model="form.visual_description" type="textarea" :rows="3" placeholder="描述画面内容..." />
          </el-form-item>
          <el-form-item label="台词">
            <el-input v-model="form.dialogue" type="textarea" :rows="2" placeholder="角色对白..." />
          </el-form-item>
          <el-form-item label="涉及角色">
            <el-select 
              v-model="form.characters" 
              multiple 
              class="w-full" 
              placeholder="选择在该分镜出现的角色"
              collapse-tags
              collapse-tags-tooltip
            >
              <el-option 
                v-for="c in store.characterList" 
                :key="c.id" 
                :label="c.name" 
                :value="c.id" 
              />
            </el-select>
          </el-form-item>
          <div class="grid grid-cols-2 gap-4">
            <el-form-item label="景别">
              <el-input v-model="form.shot_size" placeholder="全景/中景/特写..." />
            </el-form-item>
            <el-form-item label="时长(s)">
              <el-input-number v-model="form.duration" :min="0" :precision="1" :step="0.5" class="!w-full" />
            </el-form-item>
          </div>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">保存</el-button>
        </template>
    </el-dialog>

    <!-- 视频预览 -->
    <el-dialog v-model="videoVisible" title="结果预览" width="60%" destroy-on-close align-center>
      <video v-if="currentVideoUrl" :src="currentVideoUrl" controls autoplay class="w-full max-h-[70vh]"></video>
    </el-dialog>

    <input type="file" ref="importInput" class="hidden" accept=".xlsx, .xls" @change="handleImportFile" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useLoadingStore } from '@/stores/loadingStore'
import ModelSelector from '@/components/ModelSelector.vue'
import UnifiedImageCard from '@/components/UnifiedImageCard.vue'
import { 
  getShots, createShot, updateShot, deleteShot, batchDeleteShots, 
  createFusion, getFusions 
} from '@/api/project'
import { 
  generateScenePrompt, generateSceneImage 
} from '@/api/generation'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { 
  Plus, Delete, Refresh, Upload, VideoCamera, Microphone, 
  Edit, MagicStick, VideoPlay, CopyDocument 
} from '@element-plus/icons-vue'

const store = useProjectStore()
const loadingStore = useLoadingStore()

// --- State ---
const selectedIds = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const insertIndex = ref(-1)
const videoVisible = ref(false)
const currentVideoUrl = ref('')
const importInput = ref(null)

const form = ref({
  scene: '', visual_description: '', dialogue: '', characters: [], shot_size: '', duration: 0
})

// --- Computed ---

const displayList = computed(() => {
  const sceneCounts = {}
  return store.shotList.map((item, index) => {
    const sceneKey = item.scene || 'default'
    if (!sceneCounts[sceneKey]) sceneCounts[sceneKey] = 0
    sceneCounts[sceneKey]++
    return { ...item, _auto_shot_number: sceneCounts[sceneKey] }
  })
})

const selectedItems = computed(() => 
  store.shotList.filter(item => selectedIds.value.includes(item.id))
)

const isAllSelected = computed(() => 
  displayList.value.length > 0 && selectedIds.value.length === displayList.value.length
)

const isIndeterminate = computed(() => 
  selectedIds.value.length > 0 && selectedIds.value.length < displayList.value.length
)

// 融图映射表：通过 shot_id 快速找到对应的融图预览
const getRelatedFusion = (shotId) => {
  return store.fusionList.find(f => f.shot_id === shotId)
}

// --- Initialization ---

onMounted(() => {
  if (store.currentProjectId) {
    refreshList()
  }
})

const refreshList = async () => {
  store.fetchShots()
  store.fetchFusions() // 同时刷新融图数据用于预览
}

// --- Helpers ---

// 健壮的角色转换逻辑，处理 ID 和对象混合的情况
const getCharacterObjects = (chars) => {
  if (!chars || chars.length === 0) return []
  return chars.map(c => {
    const id = typeof c === 'object' ? c.id : c
    const found = store.characterList.find(x => x.id === id)
    if (found) return found
    
    // 如果 store 中找不到，但 c 本身就是对象且有 name，则保留
    if (typeof c === 'object' && c.name) return c
    
    // 最后的 fallback
    return { 
      id, 
      name: id && typeof id === 'string' && id.length > 8 ? '未知角色' : (id || '未知'), 
      image_url: '' 
    }
  })
}

// --- Batch Actions ---

const handleBatchAI = async (command) => {
  const targets = selectedIds.value.length > 0 ? selectedItems.value : store.shotList
  if (targets.length === 0) return ElMessage.warning('列表为空')

  if (command === 'prompt') {
    if (!store.genOptions.textProviderId) return ElMessage.warning('请选择文本模型')
    for (const t of targets) {
      if (t.visual_description || t.scene_description) {
        await generateScenePrompt({
          scene_id: t.id,
          project_id: store.currentProjectId,
          scene_description: t.visual_description || t.scene_description,
          provider_id: store.genOptions.textProviderId,
          model_name: store.genOptions.textModelName
        })
      }
    }
    ElNotification.success({ title: '提示词批量提交', message: `已提交 ${targets.length} 个任务` })
  } 
  
  else if (command === 'image') {
    if (!store.genOptions.imageProviderId) return ElMessage.warning('请选择生图模型')
    const hasPrompt = targets.filter(t => t.scene_prompt)
    if (hasPrompt.length === 0) return ElMessage.warning('选中项中没有已生成提示词的分镜')
    for (const t of hasPrompt) {
      await generateSceneImage({
        scene_id: t.id,
        project_id: store.currentProjectId,
        scene_prompt: t.scene_prompt,
        provider_id: store.genOptions.imageProviderId,
        model_name: store.genOptions.imageModelName
      })
    }
    ElNotification.success({ title: '生图批量提交', message: `已为 ${hasPrompt.length} 个分镜提交生图任务` })
  }

  else if (command === 'full') {
    if (!store.genOptions.textProviderId || !store.genOptions.imageProviderId) 
      return ElMessage.warning('请先配置文本和生图模型')
    
    for (const t of targets) {
      await generateScenePrompt({
        scene_id: t.id,
        project_id: store.currentProjectId,
        scene_description: t.visual_description || t.scene_description,
        provider_id: store.genOptions.textProviderId,
        model_name: store.genOptions.textModelName
      })
    }
    ElMessage.success('已启动全流程批量生成')
  }

  else if (command === 'fusion') {
    await handleBatchCopyAsFusion()
  }
}

const handleBatchCopyAsFusion = async () => {
  const targets = selectedIds.value.length > 0 ? selectedItems.value : store.shotList
  try {
    await ElMessageBox.confirm(`确定将选中的 ${targets.length} 个分镜同步到融图列表吗？`, '同步确认')
    loadingStore.start('正在同步...', '请稍候')
    for (const shot of targets) {
      if (store.fusionList.some(f => f.shot_id === shot.id)) continue
      
      const elements = (shot.characters || []).map(c => {
        const char = typeof c === 'object' ? c : store.characterList.find(x => x.id === c)
        return {
          id: `el_${Date.now()}_${Math.random()}`,
          name: char?.name || '未知角色',
          image_url: char?.image_url || '',
          type: 'character',
          character_id: char?.id
        }
      })

      await createFusion(store.currentProjectId, {
        scene: shot.scene,
        shot_number: shot.shot_number || '1',
        shot_id: shot.id,
        base_image: shot.scene_image || '',
        elements: elements,
        visual_description: shot.visual_description || shot.scene_description,
        dialogue: shot.dialogue
      })
    }
    ElMessage.success('同步完成')
    store.fetchFusions() 
  } catch (e) { console.error(e) } finally { loadingStore.stop() }
}

// --- Single Actions ---

const handleOneGen = async (type, item) => {
    if (type === 'scene') {
        if (!item.scene_prompt) {
            await generateScenePrompt({
                scene_id: item.id,
                project_id: store.currentProjectId,
                scene_description: item.visual_description || item.scene_description,
                provider_id: store.genOptions.textProviderId,
                model_name: store.genOptions.textModelName
            })
            ElMessage.success('提示词生成中，请稍后刷新')
        } else {
            await generateSceneImage({
                scene_id: item.id,
                project_id: store.currentProjectId,
                scene_prompt: item.scene_prompt,
                provider_id: store.genOptions.imageProviderId,
                model_name: store.genOptions.imageModelName
            })
            ElMessage.success('场景图生成中...')
        }
    }
}

// --- Utils ---

const toggleSelection = (id) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx > -1) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

const handleSelectAllChange = (val) => {
  selectedIds.value = val ? displayList.value.map(i => i.id) : []
}

const playVideo = (url) => {
  currentVideoUrl.value = url
  videoVisible.value = true
}

// --- Standard CRUD ---
const resetForm = () => {
  form.value = { scene: '', visual_description: '', dialogue: '', characters: [], shot_size: '', duration: 0 }
}

const openCreateDialog = () => { 
  editingId.value = null; 
  insertIndex.value = -1; 
  resetForm();
  if (store.shotList.length > 0) {
    form.value.scene = store.shotList[store.shotList.length - 1].scene
  }
  dialogVisible.value = true; 
}

const openEditDialog = (item) => { 
  editingId.value = item.id; 
  const copy = JSON.parse(JSON.stringify(item));
  // 重要：将角色对象数组转换为 ID 数组，以适配 el-select
  if (copy.characters && copy.characters.length > 0 && typeof copy.characters[0] === 'object') {
    copy.characters = copy.characters.map(c => c.id)
  }
  form.value = copy; 
  dialogVisible.value = true; 
}

const insertShot = (idx) => { 
  editingId.value = null; 
  insertIndex.value = idx + 1; 
  resetForm();
  form.value.scene = store.shotList[idx].scene;
  dialogVisible.value = true; 
}

const handleDelete = async (item) => { 
  await ElMessageBox.confirm('确定删除?'); 
  await deleteShot(store.currentProjectId, item.id); 
  store.shotList = store.shotList.filter(s => s.id !== item.id)
  ElMessage.success('删除成功')
}

const handleBatchDelete = async () => { 
  await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个分镜?`); 
  await batchDeleteShots(store.currentProjectId, selectedIds.value); 
  store.shotList = store.shotList.filter(s => !selectedIds.value.includes(s.id))
  selectedIds.value = []; 
  ElMessage.success('删除成功')
}

const submitForm = async () => {
    if (!form.value.scene) return ElMessage.warning('场次必填')
    const payload = { ...form.value, movie_id: store.currentProjectId }
    if (insertIndex.value > -1) payload.insert_index = insertIndex.value
    
    try {
      if (editingId.value) {
        const res = await updateShot(store.currentProjectId, editingId.value, payload)
        const idx = store.shotList.findIndex(s => s.id === editingId.value)
        if (idx !== -1) store.shotList[idx] = res
      } else {
        const res = await createShot(store.currentProjectId, payload)
        if (insertIndex.value > -1) store.shotList.splice(insertIndex.value, 0, res)
        else store.shotList.push(res)
      }
      dialogVisible.value = false
      ElMessage.success('保存成功')
    } catch (e) { console.error(e) }
}
</script>

<style scoped>
.shot-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  display: grid;
  grid-template-columns: 80px 1fr 220px 360px;
  gap: 16px;
  padding: 0; 
  transition: all 0.2s ease;
  position: relative;
  min-height: 120px;
}

.shot-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: #d1d5db;
  transform: translateY(-1px);
}

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
  cursor: pointer;
}

.label { font-size: 10px; color: #9ca3af; text-transform: uppercase; }
.value { font-size: 18px; font-weight: 800; color: #374151; line-height: 1.2; }
.divider-vertical { width: 20px; height: 1px; background-color: #e5e7eb; margin: 6px 0; }

.content-section { padding: 16px 0; display: flex; flex-direction: column; justify-content: center; }
.content-row { display: flex; align-items: flex-start; gap: 8px; }
.icon { margin-top: 3px; font-size: 14px; }
.icon.visual { color: #8b5cf6; } 
.icon.audio { color: #f59e0b; }  
.text-content { font-size: 13px; line-height: 1.6; color: #1f2937; }

.meta-section { padding: 16px 12px 16px 0; display: flex; flex-direction: column; align-items: flex-end; justify-content: center; }

/* 预览区块样式 */
.preview-section {
  padding: 12px;
  border-left: 1px dashed #f3f4f6;
  background-color: #fcfcfc;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
}
.preview-box { display: flex; flex-direction: column; gap: 4px; }
.preview-label { font-size: 10px; color: #9ca3af; font-weight: bold; margin-bottom: 2px; }

.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 3px; }
</style>