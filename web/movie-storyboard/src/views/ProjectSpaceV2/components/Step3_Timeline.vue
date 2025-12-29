<template>
  <div class="h-full flex flex-col bg-gray-50">
    <div class="flex-1 flex border-b border-gray-200">
      <div class="flex-1 bg-gray-900 flex items-center justify-center relative">
        <div class="text-gray-500 text-sm flex flex-col items-center gap-2">
          <span class="w-12 h-8 border-2 border-gray-700 rounded border-dashed flex items-center justify-center text-xs">REC</span>
          Main Monitor
        </div>
      </div>
      
      <div class="w-80 bg-white border-l border-gray-200 p-6 flex flex-col shadow-sm z-10">
        <h3 class="font-bold text-gray-900 mb-6 text-lg border-b border-gray-100 pb-2">导出选项</h3>
        <div class="space-y-6 flex-1">
          <div class="space-y-2">
            <label class="text-xs font-bold text-gray-500 uppercase tracking-wider">Resolution</label>
            <select class="w-full bg-gray-50 border border-gray-200 rounded-lg p-2.5 text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-200 outline-none transition-all">
              <option>1080P (16:9)</option>
              <option>4K (16:9)</option>
              <option>Vertical (9:16)</option>
            </select>
          </div>
          
          <div class="p-5 bg-gradient-to-br from-gray-50 to-white rounded-xl border border-gray-200 shadow-sm">
            <h4 class="text-sm font-bold text-gray-900 mb-2 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-pink-500"></span>
              剪映兼容导出
            </h4>
            <p class="text-xs text-gray-500 mb-4 leading-relaxed">生成包含所有分镜视频、转场和排版的 draft_content.json。</p>
            <el-button @click="exportJianying" class="w-full bg-black hover:bg-gray-800 text-white text-sm py-2.5 rounded-lg font-bold flex items-center justify-center gap-2 shadow-lg transition-all">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              导出剪映草稿
            </el-button>
          </div>
        </div>
        
        <el-button @click="$emit('prev')" class="text-gray-400 hover:text-gray-900 mt-4 text-sm transition-colors flex items-center justify-center gap-1">
          <span>←</span> 返回修改素材
        </el-button>
      </div>
    </div>

    <div class="h-72 bg-white flex flex-col select-none border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] z-20">
      <div class="h-8 border-b border-gray-200 bg-gray-50 flex items-end px-4 overflow-hidden relative">
        <div class="flex text-xs text-gray-400 space-x-10 pb-1 font-mono">
          <span v-for="i in 20" :key="i">{{ (i-1) * 5 }}s</span>
        </div>
        <div class="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 left-10 shadow-sm">
           <div class="w-3 h-3 -ml-[5px] bg-red-500 text-[8px] text-white flex items-center justify-center rounded-b absolute top-0">▼</div>
        </div>
      </div>

      <div class="flex-1 overflow-x-auto overflow-y-hidden p-4 space-y-3 relative bg-gray-50/50">
        
        <div class="h-20 bg-white border border-gray-200 rounded-lg relative w-[2000px] flex items-center px-2 shadow-sm">
          <div class="absolute left-0 top-2 text-[10px] text-gray-400 font-bold ml-2 pointer-events-none uppercase tracking-wider">Video Track</div>
          
          <div 
            v-for="(clip, idx) in timelineClips" 
            :key="idx"
            class="h-14 bg-blue-100 border border-blue-200 rounded-md cursor-move flex items-center justify-center overflow-hidden relative group hover:bg-blue-200 transition-colors shadow-sm"
            :style="{ width: clip.duration * 20 + 'px', marginLeft: '2px' }"
          >
            <div class="absolute inset-0 flex items-center justify-center opacity-20">
               <span class="text-2xl">🎬</span>
            </div>
            <div class="text-xs text-blue-900 truncate px-2 z-10 font-bold drop-shadow-sm">{{ clip.name }}</div>
            
            <div class="absolute left-0 w-1.5 h-full cursor-w-resize bg-black/10 opacity-0 group-hover:opacity-100 hover:bg-blue-500 transition-all"></div>
            <div class="absolute right-0 w-1.5 h-full cursor-w-resize bg-black/10 opacity-0 group-hover:opacity-100 hover:bg-blue-500 transition-all"></div>
          </div>
        </div>

        <div class="h-14 bg-white border border-gray-200 rounded-lg relative w-[2000px] flex items-center px-2 shadow-sm">
          <div class="absolute left-0 top-1 text-[10px] text-gray-400 font-bold ml-2 pointer-events-none uppercase tracking-wider">Audio Track</div>
           <div class="h-8 bg-green-50 border border-green-200 rounded w-64 ml-2 flex items-center justify-center relative overflow-hidden">
             <div class="flex items-center gap-0.5 h-full w-full px-1 opacity-50">
               <div v-for="n in 40" :key="n" class="w-1 bg-green-400 rounded-full" :style="{ height: Math.random() * 100 + '%' }"></div>
             </div>
             <span class="text-[10px] text-green-700 absolute z-10 font-medium">Background Music.mp3</span>
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

const timelineClips = ref([
  { id: 1, name: 'Shot 1 - Long', duration: 3, type: 'video' },
  { id: 2, name: 'Shot 2 - Medium', duration: 4, type: 'video' },
  { id: 3, name: 'Shot 3 - Close', duration: 2, type: 'video' },
  { id: 4, name: 'Shot 4', duration: 5, type: 'video' }
])

const exportJianying = () => {
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
  
  const blob = new Blob([JSON.stringify(jianyingData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `project_${props.projectId}_jianying_draft.json`
  a.click()
}
</script>