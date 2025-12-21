<template>
  <transition name="fade">
    <div v-if="store.visible" class="global-loading-mask">
      <div class="loading-dialog-box">
        <!-- 旋转的 Loading 图标 -->
        <div class="loading-spinner">
          <el-icon class="is-loading"><Loading /></el-icon>
        </div>
        
        <div class="loading-text">{{ store.title }}</div>
        <div class="loading-subtext">{{ store.subText }}</div>
        
        <div class="loading-actions">
          <el-button 
            type="danger" 
            plain 
            round 
            size="large" 
            @click="handleCancel"
          >
            <el-icon class="el-icon--left"><Close /></el-icon>
            放弃生成
          </el-button>
          
          <el-button 
            type="primary" 
            round 
            size="large" 
            disabled
          >
            <el-icon class="el-icon--left is-loading"><Loading /></el-icon>
            请耐心等待
          </el-button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { useLoadingStore } from '@/stores/loadingStore'
import { Loading, Close } from '@element-plus/icons-vue'

const store = useLoadingStore()

const handleCancel = () => {
  store.cancel()
}
</script>

<style scoped>
/* 遮罩层 */
.global-loading-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85); /* 稍微加深了一点 */
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  backdrop-filter: blur(5px); /* 增加毛玻璃效果，提升现代感 */
}

/* 弹窗主体 */
.loading-dialog-box {
  background: #fff;
  width: 360px;
  padding: 40px 30px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 旋转图标区域 */
.loading-spinner {
  font-size: 48px;
  color: #409EFF;
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

/* 主标题 */
.loading-text {
  font-size: 18px;
  color: #303133;
  margin-bottom: 12px;
  font-weight: bold;
}

/* 副标题 */
.loading-subtext {
  font-size: 14px;
  color: #909399;
  margin-bottom: 30px;
  line-height: 1.5;
}

/* 按钮区域 */
.loading-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  width: 100%;
}

/* Vue Transition 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>