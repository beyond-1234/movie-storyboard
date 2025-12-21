import { defineStore } from 'pinia'

export const useLoadingStore = defineStore('loading', {
  state: () => ({
    visible: false,
    title: '处理中...',
    subText: '请稍候',
    abortController: null // 用于取消 fetch/axios 请求
  }),
  actions: {
    /**
     * 开启全局加载
     * @param {string} title - 主标题
     * @param {string} subText - 副标题/提示语
     * @returns {AbortSignal} - 用于传入 axios 的 signal
     */
    start(title = 'AI 生成中', subText = '正在分析剧本，请勿关闭页面...') {
      this.title = title
      this.subText = subText
      this.visible = true
      
      // 创建新的控制器，用于取消请求
      this.abortController = new AbortController()
      return this.abortController.signal
    },

    /**
     * 关闭加载
     */
    stop() {
      this.visible = false
      this.abortController = null
    },

    /**
     * 用户点击“放弃”按钮
     */
    cancel() {
      if (this.abortController) {
        this.abortController.abort() // 触发 abort 信号
      }
      this.stop()
    }
  }
})