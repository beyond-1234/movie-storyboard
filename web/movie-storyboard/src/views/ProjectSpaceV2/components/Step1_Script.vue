<template>
  <div class="flex h-full w-full bg-gray-50">
    <div class="w-1/3 border-r border-gray-200 flex flex-col bg-white shadow-sm z-10">
      <div class="p-4 border-b border-gray-200 font-bold flex justify-between items-center bg-white">
        <span class="text-gray-800 text-lg">原始剧本</span>
        <el-button 
          @click="analyzeScript" 
          :disabled="loading"
          class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-1.5 rounded transition-colors disabled:opacity-50 shadow-sm"
        >
          {{ loading ? '分析中...' : '生成分镜' }}
        </el-button>
      </div>
      <div class="flex-1 p-0 relative">
        <textarea 
          v-model="scriptContent" 
          class="w-full h-full bg-gray-50 text-gray-800 p-6 resize-none focus:outline-none focus:bg-white transition-colors text-base leading-relaxed"
          placeholder="在此处粘贴你的电影剧本..."
        ></textarea>
      </div>
    </div>

    <div class="w-2/3 flex flex-col bg-gray-50">
      <div class="flex-none h-1/2 border-b border-gray-200 flex flex-col bg-gray-50">
        <div class="p-3 border-b border-gray-200 bg-white text-sm font-bold text-gray-500 flex items-center gap-2">
           <span class="w-1 h-4 bg-blue-500 rounded-full"></span>
           角色列表 (自动提取)
        </div>
        <div class="flex-1 overflow-y-auto p-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <div v-for="(char, idx) in characters" :key="idx" class="bg-white p-4 rounded-xl border border-gray-200 flex flex-col gap-3 shadow-sm hover:shadow-md transition-shadow">
             <input v-model="char.name" class="bg-transparent font-bold border-b border-gray-200 focus:border-blue-500 outline-none text-gray-900 pb-1" placeholder="姓名" />
             <textarea v-model="char.description" class="bg-gray-50 text-sm text-gray-600 p-2 rounded resize-none h-20 border-none focus:ring-1 focus:ring-blue-100" placeholder="外貌描述..."></textarea>
          </div>
          <el-button class="border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center text-gray-400 hover:text-blue-500 hover:border-blue-400 hover:bg-blue-50 transition-all h-auto min-h-[140px]" @click="addCharacter">
            <span class="text-2xl mb-1">+</span>
            <span class="text-sm">添加角色</span>
          </el-button>
        </div>
      </div>

      <div class="flex-1 flex flex-col overflow-hidden bg-gray-50">
        <div class="p-3 border-b border-gray-200 bg-white text-sm font-bold text-gray-500 flex justify-between items-center shadow-sm z-10">
          <div class="flex items-center gap-2">
            <span class="w-1 h-4 bg-green-500 rounded-full"></span>
            <span>分镜列表 ({{ shots.length }})</span>
          </div>
          <div class="space-x-3">
            <el-button @click="saveData" class="text-sm text-gray-500 hover:text-blue-600 font-medium">保存修改</el-button>
            <el-button @click="$emit('next')" class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-5 py-1.5 rounded transition-colors shadow-sm">
              下一步 >
            </el-button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto p-6 space-y-4">
          <div v-for="(shot, index) in shots" :key="index" class="bg-white p-4 rounded-xl border border-gray-200 flex gap-5 shadow-sm hover:border-blue-300 transition-colors group">
            <div class="flex-none w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-500 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">{{ index + 1 }}</div>
            <div class="flex-1 space-y-3">
              <input v-model="shot.content" class="w-full bg-transparent border-b border-gray-200 focus:border-blue-500 outline-none pb-2 text-gray-800 text-lg font-medium placeholder-gray-300" placeholder="描述分镜画面..." />
              <div class="flex gap-3">
                 <select v-model="shot.type" class="bg-gray-50 text-sm border border-gray-200 rounded px-2 py-1 text-gray-600 focus:border-blue-500 outline-none">
                    <option value="Long Shot">远景 (Long Shot)</option>
                    <option value="Medium Shot">中景 (Medium Shot)</option>
                    <option value="Close Up">特写 (Close Up)</option>
                 </select>
                 <div class="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded px-2">
                    <span class="text-xs text-gray-400">Duration:</span>
                    <input v-model="shot.duration" type="number" class="bg-transparent text-sm text-gray-700 w-12 py-1 outline-none" placeholder="3" />
                    <span class="text-xs text-gray-400">s</span>
                 </div>
              </div>
            </div>
            <el-button @click="removeShot(index)" class="text-gray-300 hover:text-red-500 transition-colors px-2 self-start">
               <span class="text-xl">×</span>
            </el-button>
          </div>
          <el-button @click="addShot" class="w-full py-4 border-2 border-dashed border-gray-300 text-gray-400 hover:text-blue-600 hover:border-blue-400 hover:bg-blue-50 rounded-xl transition-all font-medium">
            + 添加分镜
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps(['projectId'])
const emit = defineEmits(['next', 'prev'])
const loading = ref(false)
const scriptContent = ref('')

const characters = ref([])
const shots = ref([])

const analyzeScript = async () => {
  loading.value = true
  setTimeout(() => {
    characters.value = [
      { name: 'John', description: '30岁，侦探，穿着风衣，神情疲惫' },
      { name: 'Alice', description: '25岁，神秘女子，红裙' }
    ]
    shots.value = [
      { content: 'John 走进昏暗的雨夜街道，霓虹灯闪烁。', type: 'Long Shot', duration: 3 },
      { content: 'John 停下脚步，点燃一支烟。', type: 'Medium Shot', duration: 4 },
      { content: '烟头的火光照亮了他深邃的眼睛。', type: 'Close Up', duration: 2 }
    ]
    loading.value = false
  }, 1000)
}

const addCharacter = () => characters.value.push({ name: '', description: '' })
const addShot = () => shots.value.push({ content: '', type: 'Medium Shot', duration: 3 })
const removeShot = (idx) => shots.value.splice(idx, 1)
const saveData = () => {
    console.log('Saved')
}
</script>