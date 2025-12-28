<template>
  <div class="h-full flex flex-col bg-white">
    <!-- 工具栏 -->
    <div class="h-12 border-b border-gray-700 flex items-center px-4 justify-between bg-white">
      <div class="text-sm text-gray-400">共 {{ shots.length }} 个分镜待处理</div>
      <div class="space-x-2">
        <button @click="$emit('prev')" class="text-gray-400 hover:text-white text-sm px-3">上一步</button>
        <button class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1.5 rounded">批量生成所有</button>
        <button @click="$emit('next')" class="bg-green-600 hover:bg-green-500 text-white text-xs px-3 py-1.5 rounded">下一步 (剪辑)</button>
      </div>
    </div>

    <!-- 分镜流列表 -->
    <div class="flex-1 overflow-y-auto p-6 space-y-8">
      <div v-for="(shot, index) in shots" :key="index" class="bg-white rounded-lg border border-gray-700 p-4 shadow-lg">
        <!-- 分镜标题行 -->
        <div class="flex items-center justify-between mb-4 border-b border-gray-700 pb-2">
          <div class="flex items-center gap-3">
             <span class="text-2xl font-bold text-gray-600">#{{ index + 1 }}</span>
             <p class="text-white font-medium text-lg">{{ shot.content }}</p>
          </div>
          <span class="text-xs bg-white px-2 py-1 rounded text-gray-300">{{ shot.type }} / {{ shot.duration }}s</span>
        </div>

        <!-- 资产生成区域 (Grid) -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- 1. 场景与底图 -->
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-blue-400 uppercase">Step 2.1: 场景底图</span>
              <button class="text-xs hover:text-white text-gray-500">刷新Prompt</button>
            </div>
            <textarea class="w-full h-20 bg-white border border-gray-700 rounded p-2 text-xs text-gray-300 resize-none" v-model="shot.scenePrompt" placeholder="场景提示词..."></textarea>
            <div class="aspect-video bg-black rounded border border-gray-700 relative group overflow-hidden">
               <img v-if="shot.sceneImage" :src="shot.sceneImage" class="w-full h-full object-cover" />
               <div v-else class="flex items-center justify-center h-full text-gray-600 text-xs">无底图</div>
               <button class="absolute bottom-2 right-2 bg-blue-600 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">生成图片</button>
            </div>
          </div>

          <!-- 2. 分镜九宫格 -->
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-purple-400 uppercase">Step 2.2: 动态九宫格</span>
              <button class="text-xs hover:text-white text-gray-500">刷新Prompt</button>
            </div>
            <textarea class="w-full h-20 bg-white border border-gray-700 rounded p-2 text-xs text-gray-300 resize-none" v-model="shot.gridPrompt" placeholder="分镜动作提示词..."></textarea>
            <div class="aspect-video bg-black rounded border border-gray-700 relative group overflow-hidden grid grid-cols-3 grid-rows-3 gap-0.5 p-0.5">
               <!-- 模拟九宫格 -->
               <div v-for="n in 9" :key="n" class="bg-white"></div>
               <button class="absolute bottom-2 right-2 bg-purple-600 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10">生成九宫格</button>
            </div>
          </div>

          <!-- 3. 最终视频 -->
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold text-green-400 uppercase">Step 2.3: 动态视频</span>
              <button class="text-xs hover:text-white text-gray-500">刷新Prompt</button>
            </div>
            <textarea class="w-full h-20 bg-white border border-gray-700 rounded p-2 text-xs text-gray-300 resize-none" v-model="shot.videoPrompt" placeholder="视频生成提示词..."></textarea>
            <div class="aspect-video bg-black rounded border border-gray-700 relative group overflow-hidden">
               <video v-if="shot.videoUrl" :src="shot.videoUrl" controls class="w-full h-full object-cover"></video>
               <div v-else class="flex items-center justify-center h-full text-gray-600 text-xs">无视频</div>
               <button class="absolute bottom-2 right-2 bg-green-600 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">生成视频</button>
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

// 模拟从上一步继承的数据，加上 assets 字段
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