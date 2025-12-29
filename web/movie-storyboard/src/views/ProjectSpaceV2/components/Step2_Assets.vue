<template>
  <div class="h-full flex flex-col bg-gray-50">
    <div class="h-14 border-b border-gray-200 flex items-center px-6 justify-between bg-white shadow-sm z-10">
      <div class="text-sm text-gray-500 font-medium">
        <span class="bg-blue-50 text-blue-600 px-2 py-1 rounded text-xs mr-2 font-bold">PRO</span>
        共 {{ shots.length }} 个分镜待处理
      </div>
      <div class="space-x-3">
        <el-button @click="$emit('prev')" class="text-gray-500 hover:text-gray-800 text-sm px-3 font-medium">上一步</el-button>
        <el-button class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-1.5 rounded shadow-sm transition-colors">批量生成所有</el-button>
        <el-button @click="$emit('next')" class="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-1.5 rounded shadow-sm transition-colors">下一步 (剪辑)</el-button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-8 space-y-8">
      <div v-for="(shot, index) in shots" :key="index" class="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-6 border-b border-gray-100 pb-4">
          <div class="flex items-center gap-4">
             <span class="text-2xl font-bold text-gray-200 select-none">#{{ index + 1 }}</span>
             <p class="text-gray-800 font-bold text-lg">{{ shot.content }}</p>
          </div>
          <span class="text-xs bg-gray-100 text-gray-500 px-3 py-1 rounded-full border border-gray-200 font-medium">
            {{ shot.type }} / {{ shot.duration }}s
          </span>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div class="space-y-3 group">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-blue-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span> Step 2.1: 场景底图
              </span>
              <el-button class="text-xs text-gray-400 hover:text-blue-600 transition-colors">刷新Prompt</el-button>
            </div>
            <textarea class="w-full h-24 bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700 resize-none focus:bg-white focus:border-blue-500 focus:ring-1 focus:ring-blue-200 outline-none transition-all" v-model="shot.scenePrompt" placeholder="场景提示词..."></textarea>
            <div class="aspect-video bg-gray-100 rounded-lg border border-gray-200 relative overflow-hidden flex items-center justify-center">
               <img v-if="shot.sceneImage" :src="shot.sceneImage" class="w-full h-full object-cover" />
               <div v-else class="text-gray-400 text-xs flex flex-col items-center gap-2">
                 <span class="text-2xl">🖼️</span>
                 <span>等待生成</span>
               </div>
               <div class="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-end p-2 pointer-events-none">
                 <el-button class="bg-blue-600 text-white text-xs px-3 py-1.5 rounded shadow-lg pointer-events-auto hover:bg-blue-700">生成图片</el-button>
               </div>
            </div>
          </div>

          <div class="space-y-3 group">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-purple-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-purple-500"></span> Step 2.2: 动态九宫格
              </span>
              <el-button class="text-xs text-gray-400 hover:text-purple-600 transition-colors">刷新Prompt</el-button>
            </div>
            <textarea class="w-full h-24 bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700 resize-none focus:bg-white focus:border-purple-500 focus:ring-1 focus:ring-purple-200 outline-none transition-all" v-model="shot.gridPrompt" placeholder="分镜动作提示词..."></textarea>
            <div class="aspect-video bg-gray-100 rounded-lg border border-gray-200 relative overflow-hidden grid grid-cols-3 grid-rows-3 gap-0.5 p-0.5">
               <div v-for="n in 9" :key="n" class="bg-white"></div>
               <div class="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-end p-2 pointer-events-none z-10">
                  <el-button class="bg-purple-600 text-white text-xs px-3 py-1.5 rounded shadow-lg pointer-events-auto hover:bg-purple-700">生成九宫格</el-button>
               </div>
            </div>
          </div>

          <div class="space-y-3 group">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-green-600 uppercase tracking-wide flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-green-500"></span> Step 2.3: 动态视频
              </span>
              <el-button class="text-xs text-gray-400 hover:text-green-600 transition-colors">刷新Prompt</el-button>
            </div>
            <textarea class="w-full h-24 bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700 resize-none focus:bg-white focus:border-green-500 focus:ring-1 focus:ring-green-200 outline-none transition-all" v-model="shot.videoPrompt" placeholder="视频生成提示词..."></textarea>
            <div class="aspect-video bg-gray-100 rounded-lg border border-gray-200 relative overflow-hidden flex items-center justify-center">
               <video v-if="shot.videoUrl" :src="shot.videoUrl" controls class="w-full h-full object-cover"></video>
               <div v-else class="text-gray-400 text-xs flex flex-col items-center gap-2">
                 <span class="text-2xl">🎬</span>
                 <span>等待生成</span>
               </div>
               <div class="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-end p-2 pointer-events-none">
                  <el-button class="bg-green-600 text-white text-xs px-3 py-1.5 rounded shadow-lg pointer-events-auto hover:bg-green-700">生成视频</el-button>
               </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps(['projectId'])
const emit = defineEmits(['next', 'prev'])

const shots = ref([
  { 
    content: 'John 走进昏暗的雨夜街道，霓虹灯闪烁。', 
    type: 'Long Shot', 
    duration: 3,
    scenePrompt: 'Cyberpunk street, raining, neon lights, dark atmosphere, wide shot',
    sceneImage: null,
    gridPrompt: '',
    videoPrompt: '',
    videoUrl: null
  },
  { 
    content: 'John 停下脚步，点燃一支烟。', 
    type: 'Medium Shot', 
    duration: 4,
    scenePrompt: 'Man in trenchcoat holding a lighter, flame illuminating face, medium shot',
    sceneImage: null,
    gridPrompt: '',
    videoPrompt: '',
    videoUrl: null
  }
])
</script>