<template>
  <div class="flex flex-col h-screen bg-gray-900 text-white overflow-hidden">
    <!-- 顶部极简进度条 -->
    <header class="flex-none h-12 bg-gray-800 border-b border-gray-700 flex items-center px-4 justify-between select-none">
      <div class="flex items-center space-x-2">
        <span class="font-bold text-lg text-blue-400">MovieStoryboard V2</span>
        <span class="text-xs text-gray-500">Project ID: {{ route.params.id }}</span>
      </div>

      <!-- 步骤指示器 -->
      <div class="flex-1 max-w-2xl mx-auto">
        <div class="flex items-center w-full relative">
          <!-- 进度线 -->
          <div class="absolute top-1/2 left-0 w-full h-0.5 bg-gray-700 -z-0"></div>
          <div class="absolute top-1/2 left-0 h-0.5 bg-blue-500 transition-all duration-300 -z-0" :style="{ width: progressWidth }"></div>

          <!-- 步骤节点 -->
          <div 
            v-for="(step, index) in steps" 
            :key="index"
            class="flex-1 flex justify-center relative z-10 cursor-pointer group"
            @click="goToStep(index)"
          >
            <div 
              class="flex items-center space-x-2 px-3 py-1 rounded-full transition-colors duration-200"
              :class="currentStep >= index ? 'bg-gray-800 border border-blue-500 text-blue-400' : 'bg-gray-800 border border-gray-600 text-gray-500'"
            >
              <div 
                class="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
                :class="currentStep >= index ? 'bg-blue-500 text-white' : 'bg-gray-600 text-gray-300'"
              >
                {{ index + 1 }}
              </div>
              <span class="text-sm font-medium hidden sm:block">{{ step.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center space-x-3">
         <button @click="router.push('/')" class="text-gray-400 hover:text-white text-sm">退出</button>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main class="flex-1 overflow-hidden relative">
      <Transition name="fade-slide" mode="out-in">
        <component 
          :is="currentStepComponent" 
          :project-id="route.params.id"
          @next="nextStep"
          @prev="prevStep"
        />
      </Transition>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Step1Script from './components/Step1_Script.vue'
import Step2Assets from './components/Step2_Assets.vue'
import Step3Timeline from './components/Step3_Timeline.vue'

const route = useRoute()
const router = useRouter()

const steps = [
  { label: '剧本 & 分镜', component: Step1Script },
  { label: '素材生成', component: Step2Assets },
  { label: '剪辑 & 导出', component: Step3Timeline }
]

const currentStep = ref(0)

const currentStepComponent = computed(() => steps[currentStep.value].component)

const progressWidth = computed(() => {
  const percent = (currentStep.value / (steps.length - 1)) * 100
  return `${percent}%`
})

const nextStep = () => {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const goToStep = (index) => {
  // 可以添加逻辑限制不允许跳跃到未完成的步骤
  currentStep.value = index
}
</script>

<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>