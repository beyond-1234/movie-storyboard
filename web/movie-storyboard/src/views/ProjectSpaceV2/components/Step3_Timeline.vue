<template>
  <div class="h-full flex flex-col bg-white">
    <!-- 播放器预览区 -->
    <div class="flex-1 flex border-b border-gray-200">
      <div class="flex-1 bg-black flex items-center justify-center relative">
        <!-- 简单的播放器占位 -->
        <div class="text-gray-500 text-sm">Main Monitor</div>
        <!-- 这里可以放一个实际的 <video> 标签，根据时间轴当前时间动态切换 src -->
      </div>
      <div class="w-80 bg-gray-50 border-l border-gray-200 p-4 flex flex-col">
        <h3 class="font-bold text-gray-800 mb-4">导出选项</h3>
        <div class="space-y-4 flex-1">
          <div class="space-y-2">
            <label class="text-xs text-gray-600">分辨率</label>
            <select class="w-full bg-white border border-gray-300 rounded p-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none">
              <option>1080P (16:9)</option>
              <option>4K (16:9)</option>
              <option>Vertical (9:16)</option>
            </select>
          </div>
          
          <div class="p-4 bg-white rounded border border-gray-200 shadow-sm">
            <h4 class="text-sm font-bold text-gray-900 mb-2">剪映兼容导出</h4>
            <p class="text-xs text-gray-500 mb-3">生成包含所有分镜视频、转场和排版的 draft_content.json。</p>
            <button @click="exportJianying" class="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:opacity-90 text-white text-sm py-2 rounded font-bold flex items-center justify-center gap-2 shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              导出剪映草稿
            </button>
          </div>
        </div>
        
        <button @click="$emit('prev')" class="text-gray-500 hover:text-gray-900 mt-4 text-sm transition-colors">返回修改素材</button>
      </div>
    </div>

    <!-- 非线性时间轴 -->
    <div class="h-64 bg-gray-100 flex flex-col select-none border-t border-gray-200">
      <!-- 时间刻度 -->
      <div class="h-8 border-b border-gray-300 bg-gray-200 flex items-end px-4 overflow-hidden relative">
        <div class="flex text-xs text-gray-600 space-x-10">
          <span v-for="i in 20" :key="i">{{ (i-1) * 5 }}s</span>
        </div>
        <!-- 游标 -->
        <div class="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 left-10"></div>
      </div>

      <!-- 轨道区域 -->
      <div class="flex-1 overflow-x-auto overflow-y-hidden p-2 space-y-2 relative">
        
        <!-- 视频轨道 -->
        <div class="h-16 bg-white border border-gray-300 rounded relative w-[2000px] flex items-center px-2 shadow-sm">
          <div class="absolute left-0 text-xs text-gray-500 font-bold ml-2 pointer-events-none">Video Track</div>
          
          <!-- 视频片段 Block -->
          <!-- 使用 v-for 渲染分镜视频片段，支持拖拽(需要引入 dragging 库，此处模拟 UI) -->
          <div 
            v-for="(clip, idx) in timelineClips" 
            :key="idx"
            class="h-12 bg-blue-100 border border-blue-300 rounded cursor-move flex items-center justify-center overflow-hidden relative group hover:bg-blue-200 transition-colors"
            :style="{ width: clip.duration * 20 + 'px', marginLeft: '2px' }"
          >
            <div class="text-xs text-blue-800 truncate px-1 z-10 font-medium">{{ clip.name }}</div>
            
            <!-- 拖拽把手 -->
            <div class="absolute left-0 w-2 h-full cursor-w-resize hover:bg-white/50 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="absolute right-0 w-2 h-full cursor-w-resize hover:bg-white/50 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </div>
        </div>

        <!-- 音频轨道 -->
        <div class="h-10 bg-white border border-gray-300 rounded relative w-[2000px] flex items-center px-2 mt-1 shadow-sm">
          <div class="absolute left-0 text-xs text-gray-500 font-bold ml-2 pointer-events-none">Audio Track</div>
           <div class="h-6 bg-green-100 border border-green-300 rounded w-64 ml-2 opacity-90 flex items-center justify-center">
             <span class="text-[10px] text-green-800">Audio Waveform</span>
           </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps(['projectId'])
const emit = defineEmits(['prev'])

// 模拟从 Store 获取的视频片段
const timelineClips = ref([
  { id: 1, name: 'Shot 1 - Long', duration: 3, type: 'video' },
  { id: 2, name: 'Shot 2 - Medium', duration: 4, type: 'video' },
  { id: 3, name: 'Shot 3 - Close', duration: 2, type: 'video' },
  { id: 4, name: 'Shot 4', duration: 5, type: 'video' }
])

const exportJianying = () => {
  // 构建剪映兼容的 JSON 结构 (Simplified)
  const jianyingData = {
    "canvas_config": {
      "width": 1920,
      "height": 1080
    },
    "tracks": [
      {
        "type": "video",
        "segments": timelineClips.value.map(clip => ({
            "material_id": clip.id,
            "source_timerange": { "start": 0, "duration": clip.duration * 1000000 },
            "target_timerange": { "start": 0, "duration": clip.duration * 1000000 }
        }))
      }
    ]
  }
  
  // 这里可以触发文件下载或调用后端 API (jianying_exporter.py)
  console.log('Exporting Jianying JSON:', jianyingData)
  
  const blob = new Blob([JSON.stringify(jianyingData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `project_${props.projectId}_jianying_draft.json`
  a.click()
}
</script>