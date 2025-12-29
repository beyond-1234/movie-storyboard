<template>
  <div class="flex flex-col h-screen bg-gray-50 text-gray-900 overflow-hidden">
    <header class="flex-none h-14 bg-white border-b border-gray-200 flex items-center px-6 justify-between select-none shadow-sm z-20">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold shadow-sm">M</div>
        <div class="flex flex-col">
           <span class="font-bold text-base text-gray-800 leading-tight">MovieStoryboard</span>
           <span class="text-[10px] text-gray-400 leading-tight">Project ID: {{ route.params.id }}</span>
        </div>
      </div>

      <div class="flex-1 max-w-2xl mx-auto">
        <div class="flex items-center w-full relative">
          <div class="absolute top-1/2 left-0 w-full h-0.5 bg-gray-200 -z-0"></div>
          <div class="absolute top-1/2 left-0 h-0.5 bg-blue-600 transition-all duration-300 -z-0" :style="{ width: progressWidth }"></div>

          <div 
            v-for="(step, index) in steps" 
            :key="index"
            class="flex-1 flex justify-center relative z-10 cursor-pointer group"
            @click="goToStep(index)"
          >
            <div 
              class="flex items-center space-x-2 px-3 py-1.5 rounded-full transition-all duration-200 border"
              :class="currentStep >= index ? 'bg-blue-50 border-blue-200 text-blue-700 shadow-sm' : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'"
            >
              <div 
                class="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold transition-colors"
                :class="currentStep >= index ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'"
              >
                {{ index + 1 }}
              </div>
              <span class="text-sm font-medium hidden sm:block">{{ step.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center space-x-3">
         <button @click="router.push('/')" class="text-gray-500 hover:text-gray-900 text-sm font-medium px-3 py-1.5 rounded hover:bg-gray-100 transition-colors">退出项目</button>
      </div>
    </header>

    <main class="flex-1 overflow-hidden relative bg-gray-50">
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
  transform: translateX(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>