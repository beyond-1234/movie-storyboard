<template>
  <el-dialog 
    v-model="visible" 
    title="项目资源历史回溯" 
    width="80%" 
    top="5vh"
    destroy-on-close
    @open="fetchHistory"
  >
    <!-- 顶部筛选栏 -->
    <div class="flex gap-4 mb-4 items-center">
      <el-radio-group v-model="filterType" size="default" @change="handleFilter">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="character">角色</el-radio-button>
        <el-radio-button label="shot">场景/分镜</el-radio-button>
        <el-radio-button label="fusion">融图/视频</el-radio-button>
      </el-radio-group>
      
      <div class="flex-1"></div>
      
      <el-input 
        v-model="searchKeyword" 
        placeholder="搜索资源名称..." 
        prefix-icon="Search"
        class="w-64"
        clearable
        @input="handleFilter"
      />
    </div>

    <!-- 列表展示区域 -->
    <el-table 
      :data="filteredList" 
      height="600" 
      border 
      stripe 
      v-loading="loading" 
      row-key="id"
    >
      <!-- 预览列 -->
      <el-table-column label="预览" width="320">
        <template #default="{ row }">
          <div class="w-full h-40 bg-gray-100 rounded border flex items-center justify-center overflow-hidden relative group">
            
            <!-- 图片预览 -->
            <el-image 
              v-if="row.media_type === 'image'" 
              :src="row.url" 
              :preview-src-list="[row.url]"
              fit="contain" 
              class="w-full h-full"
              hide-on-click-modal
            >
              <template #error>
                <div class="flex flex-col items-center text-gray-400">
                  <el-icon size="24"><Picture /></el-icon>
                  <span class="text-xs mt-1">加载失败</span>
                </div>
              </template>
            </el-image>

            <!-- 视频预览 -->
            <div v-else-if="row.media_type === 'video'" class="w-full h-full relative cursor-pointer" @click="openVideo(row.url)">
              <video :src="row.url" class="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"></video>
              <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                <el-icon size="40" class="text-white drop-shadow-md"><VideoPlay /></el-icon>
              </div>
            </div>

            <div v-else class="text-gray-400 text-xs">不支持预览</div>
          </div>
        </template>
      </el-table-column>
      
      <!-- 信息列 -->
      <el-table-column prop="entity_name" label="所属对象" min-width="180" sortable>
        <template #default="{ row }">
          <div class="font-bold text-gray-700">{{ row.entity_name }}</div>
          <div class="text-xs text-gray-400 mt-1 truncate" :title="row.filename">{{ row.filename }}</div>
        </template>
      </el-table-column>

      <el-table-column label="类型" width="100" prop="entity_type" align="center">
        <template #default="{ row }">
          <el-tag size="small" v-if="row.entity_type==='character'">角色</el-tag>
          <el-tag size="small" type="success" v-else-if="row.entity_type==='shot'">场景</el-tag>
          <el-tag size="small" type="warning" v-else-if="row.entity_type==='fusion'">融图</el-tag>
          <el-tag size="small" type="info" v-else>其他</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="version" label="版本" width="90" align="center" sortable>
        <template #default="{ row }">
          <el-tag effect="plain" type="info" size="small">v{{ row.version }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="date_str" label="生成时间" width="180" sortable />

      <!-- 操作列 -->
      <el-table-column label="操作" width="150" fixed="right" align="center">
        <template #default="{ row }">
          <div class="flex flex-col gap-2 items-center">
            <el-button 
              type="primary" 
              size="small" 
              plain 
              icon="RefreshLeft" 
              class="w-full !ml-0"
              @click="handleRestore(row)"
            >
              恢复使用
            </el-button>
            <el-button 
              type="info" 
              size="small" 
              link 
              icon="Download" 
              class="w-full !ml-0"
              @click="downloadFile(row)"
            >
              下载原文件
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 视频预览弹窗 -->
    <el-dialog v-model="videoVisible" title="视频预览" width="60%" append-to-body destroy-on-close align-center>
      <video v-if="currentVideoUrl" :src="currentVideoUrl" controls autoplay class="w-full max-h-[70vh]"></video>
    </el-dialog>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { getProjectHistory, updateCharacter, updateShot, updateFusion } from '@/api/project'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Picture, VideoPlay, RefreshLeft, Download } from '@element-plus/icons-vue'

const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue', 'restore-success'])

const store = useProjectStore()

// State
const loading = ref(false)
const fullList = ref([]) // 原始数据
const filteredList = ref([]) // 过滤后的数据
const filterType = ref('all')
const searchKeyword = ref('')

const videoVisible = ref(false)
const currentVideoUrl = ref('')

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// Methods
const fetchHistory = async () => {
  if (!store.currentProjectId) return
  
  loading.value = true
  try {
    const res = await getProjectHistory(store.currentProjectId)
    fullList.value = res || []
    handleFilter() // 初始过滤
  } catch (e) {
    console.error(e)
    ElMessage.error('获取历史记录失败')
  } finally {
    loading.value = false
  }
}

// 核心过滤逻辑
const handleFilter = () => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  const type = filterType.value

  filteredList.value = fullList.value.filter(item => {
    // 1. 类型过滤
    let typeMatch = true
    if (type !== 'all') {
      if (type === 'fusion') {
        // 融图分类包含 fusion 和 element
        typeMatch = item.entity_type === 'fusion' || item.entity_type === 'element'
      } else {
        typeMatch = item.entity_type === type
      }
    }

    // 2. 关键词过滤
    let keywordMatch = true
    if (keyword) {
      const name = (item.entity_name || '').toLowerCase()
      const filename = (item.filename || '').toLowerCase()
      keywordMatch = name.includes(keyword) || filename.includes(keyword)
    }

    return typeMatch && keywordMatch
  })
}

// 视频预览
const openVideo = (url) => {
  currentVideoUrl.value = url
  videoVisible.value = true
}

// 下载文件
const downloadFile = (row) => {
  const link = document.createElement('a')
  link.href = row.url
  link.download = row.filename || `download_${Date.now()}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 恢复历史版本
const handleRestore = async (item) => {
  try {
    await ElMessageBox.confirm(
      `确定要将【${item.entity_name}】恢复到版本 v${item.version} 吗？\n当前使用的资源将被替换。`, 
      '确认恢复', 
      { type: 'warning', confirmButtonText: '确定恢复' }
    )

    // 根据 entity_type 调用不同的更新接口
    if (item.entity_type === 'character') {
      // 1. 更新后端
      await updateCharacter(store.currentProjectId, item.entity_id, { image_url: item.url })
      
      // 2. 更新本地 Store (实现界面即时刷新)
      const char = store.characterList.find(c => c.id === item.entity_id)
      if (char) char.image_url = item.url
      
    } else if (item.entity_type === 'shot') {
      // 场景通常恢复的是 scene_image
      await updateShot(store.currentProjectId, item.entity_id, { scene_image: item.url })
      
      // 更新 Store 中的 Shot List
      // 注意：ShotList 可能在 store 中没有全量缓存，建议触发 store.fetchShots()
      store.fetchShots() // 重新拉取列表以确保数据一致
      
    } else if (item.entity_type === 'fusion') {
      // 融图比较复杂，可能是视频或图片
      const payload = {}
      if (item.media_type === 'video') {
        payload.video_url = item.url
      } else {
        // 默认认为是结果图 (result_image/首帧)
        // 如果系统区分首帧/尾帧，后端历史记录可能需要额外字段标记，或者这里简单处理为 result_image
        payload.result_image = item.url 
      }
      
      await updateFusion(store.currentProjectId, item.entity_id, payload)
      
      // 刷新融图列表
      // 同样建议触发外部刷新，因为融图列表通常在组件内维护
      emit('restore-success', 'fusion') 
    }

    ElMessage.success('恢复成功')
    
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('恢复失败')
    }
  }
}
</script>