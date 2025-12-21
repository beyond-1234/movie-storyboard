import request from '@/api/index'

// ==========================================
// 剧集 (Series) 相关
// ==========================================

export const getSeriesList = () => {
  return request.get('/series')
}

export const createSeries = (data) => {
  return request.post('/series', data)
}

export const updateSeries = (id, data) => {
  return request.put(`/series/${id}`, data)
}

export const deleteSeries = (id) => {
  return request.delete(`/series/${id}`)
}

export const getSeriesEpisodes = (seriesId) => {
  return request.get(`/series/${seriesId}/episodes`)
}

// ==========================================
// 项目 (Project) 基础
// ==========================================

// 获取项目列表 (支持 ?series_id=xxx)
export const getProjects = (params) => {
  return request.get('/projects', { params })
}

export const getProjectDetail = (id) => {
  return request.get(`/projects/${id}`)
}

export const createProject = (data) => {
  return request.post('/projects', data)
}

export const updateProject = (id, data) => {
  return request.put(`/projects/${id}`, data)
}

export const deleteProject = (id) => {
  return request.delete(`/projects/${id}`)
}

export const getProjectHistory = (id) => {
  return request.get(`/projects/${id}/history`)
}

// 导出剪映草稿
export const exportJianyingDraft = (projectId) => {
  // 注意：下载文件需要特殊处理，通常返回 blob
  return request.post(`/projects/${projectId}/export/jianying`, {}, {
    responseType: 'blob'
  })
}

// ==========================================
// 剧本 (Script)
// ==========================================

export const getScript = (projectId) => {
  return request.get(`/projects/${projectId}/script`)
}

export const saveScript = (projectId, sections) => {
  return request.post(`/projects/${projectId}/script`, sections)
}

// ==========================================
// 角色 (Character)
// ==========================================

export const getCharacters = (projectId) => {
  return request.get(`/projects/${projectId}/characters`)
}

export const createCharacter = (projectId, data) => {
  return request.post(`/projects/${projectId}/characters`, data)
}

export const updateCharacter = (projectId, charId, data) => {
  return request.put(`/projects/${projectId}/characters/${charId}`, data)
}

export const deleteCharacter = (projectId, charId) => {
  return request.delete(`/projects/${projectId}/characters/${charId}`)
}

export const batchDeleteCharacters = (projectId, ids) => {
  return request.post(`/projects/${projectId}/characters/batch_delete`, { ids })
}

// ==========================================
// 分镜/场景 (Shot)
// ==========================================

export const getShots = (projectId) => {
  return request.get(`/projects/${projectId}/shots`)
}

export const createShot = (projectId, data) => {
  return request.post(`/projects/${projectId}/shots`, data)
}

export const updateShot = (projectId, shotId, data) => {
  return request.put(`/projects/${projectId}/shots/${shotId}`, data)
}

export const deleteShot = (projectId, shotId) => {
  return request.delete(`/projects/${projectId}/shots/${shotId}`)
}

export const batchDeleteShots = (projectId, ids) => {
  return request.post(`/projects/${projectId}/shots/batch_delete`, { ids })
}

// ==========================================
// 融图任务 (Fusion Task) - 实体 CRUD
// ==========================================

export const getFusions = (projectId) => {
  return request.get(`/projects/${projectId}/fusions`)
}

export const createFusion = (projectId, data) => {
  return request.post(`/projects/${projectId}/fusions`, data)
}

export const updateFusion = (projectId, fusionId, data) => {
  return request.put(`/projects/${projectId}/fusions/${fusionId}`, data)
}

export const deleteFusion = (projectId, fusionId) => {
  return request.delete(`/projects/${projectId}/fusions/${fusionId}`)
}