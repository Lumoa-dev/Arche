import { createRouter, createWebHistory } from 'vue-router'
import { staticRoutes } from './modules/static'

const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes
})

export default router
