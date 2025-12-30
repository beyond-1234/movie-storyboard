import request from '@/api/index'

// ==========================================
// 配置与模型
// ==========================================

export const getProviders = () => {
  return request.get('/settings')
}

// ==========================================
// AI 分析 (Analysis)
// ==========================================

// 新增：分析剧本以生成剧集设定
export const analyzeSeriesScript = (data) => {
  // data: { content, provider_id, model_name }
  return request.post('/generate/analyze_series', data)
}

// 风格分析 (上传图片进行分析)
export const analyzeImage = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/generate/analyze_image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 剧本分析 (一键转分镜)
export const analyzeScript = (data) => {
  // data: { content, project_id, provider_id, model_name }
  return request.post('/generate/analyze_script', data)
}

// 剧本续写
export const scriptContinuation = (data) => {
  // data: { context_text, project_info, provider_id, model_name }
  return request.post('/generate/script_continuation', data)
}

// ==========================================
// 角色生成 (Character Gen)
// ==========================================

// 从设定生成角色列表
export const generateCharacterList = (data) => {
  // data: { visual_consistency_prompt, provider_id, model_name }
  return request.post('/generate/character_list', data)
}

// 生成角色三视图/设计图 (异步)
export const generateCharacterViews = (data) => {
  // data: { character_id, project_id, character_description, provider_id, model_name }
  return request.post('/async/generate/character_views', data)
}

// ==========================================
// 场景生成 (Scene Gen)
// ==========================================

// 生成场景提示词 (异步)
export const generateScenePrompt = (data) => {
  // data: { scene_description, project_id, scene_id, provider_id, model_name }
  return request.post('/async/generate/scene_prompt', data)
}

// 生成场景图片 (异步)
export const generateSceneImage = (data) => {
  // data: { scene_id, project_id, scene_prompt, provider_id, model_name }
  return request.post('/async/generate/scene_image', data)
}

// ==========================================
// 融图与视频生成 (Fusion Gen)
// ==========================================

// 生成融图提示词 (异步)
export const generateFusionPrompt = (data) => {
  // data: { id, fusion_id, scene_description, shot_description, element_mapping, ... }
  return request.post('/async/generate/fusion_prompt', data)
}

// 生成融图 (支持首帧和尾帧) (异步)
export const generateFusionImage = (data) => {
  // data: { fusion_id, project_id, fusion_prompt, provider_id, model_name, end_frame_prompt? }
  return request.post('/async/generate/fusion_image', data)
}

// 生成融图视频 (异步)
export const generateFusionVideo = (data) => {
  // data: { fusion_id, project_id, provider_id, model_name }
  return request.post('/async/generate/fusion_video', data)
}

// 生成元素图片 (同步/较快)
export const generateElementImage = (data) => {
  // data: { element_id, prompt, provider_id, model_name }
  return request.post('/generate/element_image', data)
}

// ==========================================
// 九宫格生成 (Grid Gen) [新增]
// ==========================================

// 生成九宫格提示词
export const generateGridPrompt = (data) => {
  // data: { scene_description, shot_description, character_names, provider_id, model_name }
  return request.post('/generate/grid_prompt', data)
}

// 生成九宫格图片 (异步)
export const generateGridImage = (data) => {
  // data: { shot_id, project_id, grid_prompt, base_image_url, character_images, provider_id, model_name }
  return request.post('/async/generate/grid_image', data)
}

// ==========================================
// 文件上传 (Uploads)
// ==========================================

export const uploadCharacterImage = (formData) => {
  return request.post('/upload/character_image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const uploadSceneImage = (formData) => {
  return request.post('/upload/scene_image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 用于融图的底图、首帧、尾帧上传
export const uploadBaseImage = (formData) => {
  // formData 需要包含 fusion_id 和 file
  return request.post('/upload/base_image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const uploadElementImage = (formData) => {
  // formData 需要包含 element_id 和 file
  return request.post('/upload/element_image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const uploadGridImage = (formData) => {
  // formData 需要包含 element_id 和 file
  return request.post('/upload/grid_image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}