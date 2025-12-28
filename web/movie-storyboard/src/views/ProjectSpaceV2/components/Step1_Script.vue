<template>
  <div class="flex h-full w-full">
    <!-- 左侧：剧本编辑 -->
    <div class="w-1/3 border-r border-gray-700 flex flex-col bg-white">
      <div class="p-3 border-b border-gray-700 font-bold flex justify-between items-center">
        <span>原始剧本</span>
        <button 
          @click="analyzeScript" 
          :disabled="loading"
          class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded disabled:opacity-50"
        >
          {{ loading ? '分析中...' : '生成分镜' }}
        </button>
      </div>
      <div class="flex-1 p-0">
        <textarea 
          v-model="scriptContent" 
          class="w-full h-full bg-white text-gray-300 p-4 resize-none focus:outline-none focus:bg-white transition-colors text-sm leading-relaxed"
          placeholder="在此处粘贴你的电影剧本..."
        ></textarea>
      </div>
    </div>

    <!-- 右侧：分镜与角色列表 -->
    <div class="w-2/3 flex flex-col bg-white">
      <div class="flex-none h-1/2 border-b border-gray-700 flex flex-col">
        <div class="p-2 border-b border-gray-700 bg-white text-sm font-bold text-gray-400">角色列表 (自动提取)</div>
        <div class="flex-1 overflow-y-auto p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <div v-for="(char, idx) in characters" :key="idx" class="bg-white p-3 rounded border border-gray-700 flex flex-col gap-2">
             <input v-model="char.name" class="bg-transparent font-bold border-b border-gray-600 focus:border-blue-500 outline-none text-white" placeholder="姓名" />
             <textarea v-model="char.description" class="bg-white text-xs text-gray-400 p-1 rounded resize-none h-16" placeholder="外貌描述..."></textarea>
          </div>
          <button class="border border-dashed border-gray-600 rounded flex items-center justify-center text-gray-500 hover:text-white h-28" @click="addCharacter">
            + 添加角色
          </button>
        </div>
      </div>

      <div class="flex-1 flex flex-col overflow-hidden">
        <div class="p-2 border-b border-gray-700 bg-white text-sm font-bold text-gray-400 flex justify-between">
          <span>分镜列表 ({{ shots.length }})</span>
          <div class="space-x-2">
            <button @click="saveData" class="text-xs text-green-400 hover:text-green-300">保存修改</button>
            <button @click="$emit('next')" class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-1 rounded">
              下一步 >
            </button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto p-4 space-y-3">
          <div v-for="(shot, index) in shots" :key="index" class="bg-white p-3 rounded border border-gray-700 flex gap-4">
            <div class="flex-none w-8 h-8 bg-white rounded-full flex items-center justify-center font-bold text-gray-400">{{ index + 1 }}</div>
            <div class="flex-1 space-y-2">
              <input v-model="shot.content" class="w-full bg-transparent border-b border-gray-600 focus:border-blue-500 outline-none pb-1" placeholder="分镜描述..." />
              <div class="flex gap-2">
                 <select v-model="shot.type" class="bg-white text-xs border border-gray-600 rounded p-1">
                    <option value="Long Shot">远景 (Long Shot)</option>
                    <option value="Medium Shot">中景 (Medium Shot)</option>
                    <option value="Close Up">特写 (Close Up)</option>
                 </select>
                 <input v-model="shot.duration" type="number" class="bg-white text-xs border border-gray-600 rounded p-1 w-20" placeholder="时长(s)" />
              </div>
            </div>
            <button @click="removeShot(index)" class="text-red-500 hover:text-red-400">×</button>
          </div>
          <button @click="addShot" class="w-full py-2 border border-dashed border-gray-600 text-gray-500 hover:text-white rounded">+ 添加分镜</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectStore } from '../../../stores/projectStore' // 假设存在

const props = defineProps(['projectId'])
const emit = defineEmits(['next', 'prev'])
const loading = ref(false)
const scriptContent = ref('')

// 模拟数据结构
const characters = ref([])
const shots = ref([])

const analyzeScript = async () => {
  loading.value = true
  // 模拟 API 调用
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
  }, 1500)
}

const addCharacter = () => characters.value.push({ name: '', description: '' })
const addShot = () => shots.value.push({ content: '', type: 'Medium Shot', duration: 3 })
const removeShot = (idx) => shots.value.splice(idx, 1)
const saveData = () => {
    console.log('Saved:', { script: scriptContent.value, characters: characters.value, shots: shots.value })
    // 这里应该调用 Store 或 API 保存数据
}
</script>