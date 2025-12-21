import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/series'
  },
  {
    path: '/series',
    name: 'SeriesList',
    // 路由懒加载
    component: () => import('@/views/SeriesList.vue') 
  },
  {
    path: '/project/:id',
    name: 'ProjectSpace',
    component: () => import('@/views/ProjectSpace/index.vue'),
    props: true // 允许组件通过 props 接收路由参数 id
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router