import os
import time
import json
import base64
import mimetypes
import logging
import requests
import uuid
import hmac
import hashlib
from http import HTTPStatus
from typing import Dict, Any, Optional, List
from zai import ZhipuAiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger("AIService")

# 尝试导入 dashscope (仅用于阿里云)
try:
    import dashscope
    from dashscope import ImageSynthesis, VideoSynthesis, MultiModalConversation, Generation
    from dashscope.audio.tts import SpeechSynthesizer 
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.warning("DashScope SDK not found. Aliyun features will be disabled.")

# --- 通用工具 ---

def _safe_log_payload(payload: Dict) -> str:
    """
    辅助函数：安全地记录 Payload，将过长的 Base64 字符串截断，防止日志爆炸。
    """
    if not payload:
        return "{}"
    try:
        # 浅拷贝以免修改原数据
        log_data = payload.copy()
        # 需要截断的字段名列表
        keys_to_truncate = ['images', 'image', 'image_url', 'binary_data_base64', 'first_frame_image', 'last_frame_image', 'image_file', 'first_frame_url', 'last_frame_url']
        
        for key in keys_to_truncate:
            if key in log_data:
                val = log_data[key]
                if isinstance(val, list):
                    # 列表中的 Base64 字符串
                    log_data[key] = [f"<Base64 Data (len={len(v)})>" if isinstance(v, str) and len(v) > 200 else v for v in val]
                elif isinstance(val, str) and len(val) > 200:
                    # 单个 Base64 字符串
                    log_data[key] = f"<Base64 Data (len={len(val)})>"
        
        # 针对 MiniMax subject_reference 特殊结构的递归处理
        if 'subject_reference' in log_data and isinstance(log_data['subject_reference'], list):
            new_refs = []
            for ref in log_data['subject_reference']:
                if isinstance(ref, dict):
                    new_ref = ref.copy()
                    if 'image_file' in new_ref and len(str(new_ref['image_file'])) > 200:
                        new_ref['image_file'] = f"<Base64 Data (len={len(str(new_ref['image_file']))})>"
                    new_refs.append(new_ref)
                else:
                    new_refs.append(ref)
            log_data['subject_reference'] = new_refs

        return json.dumps(log_data, ensure_ascii=False)
    except Exception as e:
        return f"<Error parsing payload for logging: {str(e)}>"

# ============================================================
#  Provider Handlers (不同提供商的实现)
# ============================================================

class AliyunHandler:
    @staticmethod
    def generate_text(messages, config):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key') or os.getenv("DASHSCOPE_API_KEY")
        model = config.get('model_name') or 'qwen-plus'
        
        logger.info(f"[Aliyun] Text Gen Request. Model: {model}, Msg Count: {len(messages)}")
        try:
            rsp = Generation.call(api_key=api_key, model=model, messages=messages, result_format='message')
            if rsp.status_code == HTTPStatus.OK:
                content = rsp.output.choices[0].message.content
                logger.info(f"[Aliyun] Text Gen Success. Length: {len(content)}")
                return {'success': True, 'content': content}
            
            logger.error(f"[Aliyun] Text Gen Failed. Code: {rsp.code}, Msg: {rsp.message}")
            return {'success': False, 'error_msg': rsp.message}
        except Exception as e:
            logger.exception(f"[Aliyun] Text Gen Exception")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key')
        model = config.get('model_name') or 'qwen-image-plus'
        
        logger.info(f"[Aliyun] Image Gen Request. Model: {model}, Prompt: {prompt[:50]}...")
        try:
            rsp = MultiModalConversation.call(
                api_key=api_key, model=model, messages=[{"role": "user", "content": [{"text": prompt}]}],
                result_format='message'
            )
            if rsp.status_code == HTTPStatus.OK:
                try:
                    content = rsp.output.choices[0].message.content
                    img_url = next((item['image'] for item in content if 'image' in item), None)
                    if img_url:
                        # 使用 MediaManager 下载，自动处理版本
                        saved_url = media_manager.download_from_url(img_url, 'image', entity_id)
                        if saved_url:
                            return {'success': True, 'url': saved_url}
                        return {'success': False, 'error_msg': "Download failed"}
                except Exception as e:
                    logger.error(f"[Aliyun] Image Parse Error: {e}")
                    return {'success': False, 'error_msg': f"Parse failed: {e}"}
            
            logger.error(f"[Aliyun] Image Gen API Fail: {getattr(rsp, 'message', 'Unknown')}")
            return {'success': False, 'error_msg': getattr(rsp, 'message', 'Unknown Error')}
        except Exception as e:
            logger.exception("[Aliyun] Image Gen Exception")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_video(prompt, media_manager, config, start_img=None, end_img=None, entity_id=None):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key')
        model = config.get('model_name') or 'wanx2.1-kf2v-plus'
        
        logger.info(f"[Aliyun] Video Gen Request. Model: {model}, Prompt: {prompt[:30]}...")
        
        params = {'model': model, 'prompt': prompt, 'prompt_extend': True, 'watermark': False}
        
        # 使用 MediaManager 转换 Base64
        if start_img: 
            b64 = media_manager.file_to_base64(start_img)
            if b64: params['first_frame_url'] = b64
        if end_img: 
            b64 = media_manager.file_to_base64(end_img)
            if b64: params['last_frame_url'] = b64
        
        try:
            logger.info(f"[Aliyun] Video Params: {_safe_log_payload(params)}")
            rsp = VideoSynthesis.call(api_key=api_key, **params)
            if rsp.status_code == HTTPStatus.OK:
                video_url = rsp.output.video_url
                logger.info(f"[Aliyun] Video Gen Success. TaskID: {rsp.output.task_id}, URL: {video_url}")
                # 使用 MediaManager 下载
                saved_url = media_manager.download_from_url(video_url, 'video', entity_id)
                if saved_url:
                    return {'success': True, 'url': saved_url}
                return {'success': False, 'error_msg': "Download failed"}
            logger.error(f"[Aliyun] Video Gen API Fail: {getattr(rsp, 'message', 'Unknown')}")
            return {'success': False, 'error_msg': getattr(rsp, 'message', 'Unknown Error')}
        except Exception as e:
            logger.exception("[Aliyun] Video Gen Exception")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_voice(text, media_manager, config, entity_id=None):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key')
        model = config.get('model_name') or 'qwen3-tts-flash'
        
        logger.info(f"[Aliyun] Voice Gen Request. Model: {model}, Text Len: {len(text)}")
        base_url = config.get('base_url', '')
        if base_url:
            dashscope.base_http_api_url = base_url

        try:
            rsp = SpeechSynthesizer.call(model=model, api_key=api_key, text=text, format='mp3')
            if rsp.status_code == HTTPStatus.OK:
                if hasattr(rsp, 'get_audio_data'):
                    audio_data = rsp.get_audio_data()
                    if audio_data:
                        # 使用 MediaManager 保存二进制
                        saved_url = media_manager.save_binary(audio_data, 'audio', entity_id, '.mp3')
                        return {'success': True, 'url': saved_url}
                logger.error("[Aliyun] No audio data in response")
                return {'success': False, 'error_msg': "No audio data in response"}
            
            logger.error(f"[Aliyun] Voice Gen API Fail: {getattr(rsp, 'message', 'Unknown')}")
            return {'success': False, 'error_msg': getattr(rsp, 'message', 'Unknown Error')}
        except Exception as e:
            logger.exception("[Aliyun] Voice Gen Exception")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def fuse_image(prompt, media_manager, config, base_image_path, ref_image_path_list, entity_id=None):
        """
        AliyunHandler: 图生图/融合图方法
        使用 ImageSynthesis.call 和 wan2.5-i2i-preview 模型
        支持 Base64 编码的图片输入
        """
        if not DASHSCOPE_AVAILABLE: 
            return {'success': False, 'error_msg': "DashScope SDK not installed"}
        
        api_key = config.get('api_key')
        # 默认使用 wan2.5-i2i-preview 模型，如果配置中未指定
        model = config.get('model_name') or 'wan2.5-i2i-preview'
        
        logger.info(f"[Aliyun] Fusion Request. Model: {model}, BaseImg: {base_image_path}, RefCount: {len(ref_image_path_list)}")

        if len(ref_image_path_list) + 1 > 3:
            return {'success': False, 'error_msg': "阿里云图生图模型最多支持3张参考图片"}
        
        # 准备图片列表 (Base64编码)
        images_input = []
        
        # 处理参考图片列表
        if ref_image_path_list:
            for ref_path in ref_image_path_list:
                ref_b64 = media_manager.file_to_base64(ref_path)
                if ref_b64: images_input.append(ref_b64)
                    
        # 处理基础图片
        if base_image_path:
            base_b64 = media_manager.file_to_base64(base_image_path)
            if base_b64: images_input.append(base_b64)
            else: return {'success': False, 'error_msg': f"Failed to encode base image"}
        
        if not images_input:
            return {'success': False, 'error_msg': "No input images provided for fusion"}

        # 如果有自定义 Base URL (例如新加坡节点)
        base_url = config.get('base_url')
        if base_url:
            dashscope.base_http_api_url = base_url

        try:
            logger.info(f"[Aliyun] Calling ImageSynthesis.call with model={model}, images_count={len(images_input)}")
            
            # 调用 DashScope 图像合成接口
            rsp = ImageSynthesis.call(
                api_key=api_key,
                model=model,
                prompt=prompt,
                images=images_input, # 支持 Base64 列表
                n=1,
                prompt_extend=config.get('prompt_extend', True),
                watermark=config.get('watermark', False),
                seed=int(config.get('seed', 12345))
            )
            
            if rsp.status_code == HTTPStatus.OK and hasattr(rsp, 'output') and len(rsp.output.results) > 0:
                img_url = rsp.output.results[0].url
                saved_url = media_manager.download_from_url(img_url, 'image', entity_id)

                if saved_url: 
                    logger.info(f"[Aliyun] Fusion image saved to: {saved_url}")
                    return {'success': True, 'url': saved_url}
                return {'success': True, 'url': img_url} # Fallback
            logger.warning(f"[Aliyun] Download failed, returning remote URL")
            return {'success': False, 'error_msg': getattr(rsp, 'message', 'Unknown Error')}
        except Exception as e:
            logger.exception("[Aliyun] Fusion generation failed")
            return {'success': False, 'error_msg': str(e)}

class OpenAICompatibleHandler:
    @staticmethod
    def _get_headers(config):
        return {
            "Authorization": f"Bearer {config.get('api_key')}",
            "Content-Type": "application/json"
        }

    @staticmethod
    def generate_text(messages, config):
        base_url = config.get('base_url', 'https://api.siliconflow.cn/v1')
        url = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": config.get('model_name', 'Qwen/Qwen2.5-7B-Instruct'),
            "messages": messages,
            "stream": False
        }
        
        logger.info(f"[OpenAI-Compat] Text Req: URL={url}, Model={payload['model']}")
        try:
            resp = requests.post(url, json=payload, headers=OpenAICompatibleHandler._get_headers(config), timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                content = data['choices'][0]['message']['content']
                logger.info(f"[OpenAI-Compat] Text Success. Length: {len(content)}")
                return {'success': True, 'content': content}
            
            logger.error(f"[OpenAI-Compat] Text Fail: {resp.status_code} - {resp.text[:200]}")
            return {'success': False, 'error_msg': resp.text}
        except Exception as e:
            logger.exception("[OpenAI-Compat] Text Exception")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        base_url = config.get('base_url', 'https://api.siliconflow.cn/v1')
        url = f"{base_url.rstrip('/')}/images/generations"
        payload = {
            "model": config.get('model_name', 'black-forest-labs/FLUX.1-schnell'),
            "prompt": prompt,
            "image_size": "1024x1024",
            "batch_size": 1
        }
        logger.info(f"[OpenAI-Compat] Image Req: URL={url}, Model={payload['model']}")
        
        try:
            resp = requests.post(url, json=payload, headers=OpenAICompatibleHandler._get_headers(config), timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data'):
                    img_url = data['data'][0]['url']
                    saved_url = media_manager.download_from_url(img_url, 'image', entity_id)
                    return {'success': True, 'url': saved_url or img_url}
            logger.error(f"[OpenAI-Compat] Image Fail: {resp.status_code} - {resp.text[:200]}")
            return {'success': False, 'error_msg': resp.text}
        except Exception as e:
            logger.exception("[OpenAI-Compat] Image Exception")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def fuse_image(prompt, save_dir, url_prefix, config, base_image_path, ref_image_path_list):
        """
        OpenAICompatibleHandler (SiliconFlow/RunningHub): 图生图/融合图方法
        OpenAI API 兼容接口通常通过 images/generations 实现文生图，图生图需要专门的 API 或参数。
        目前未针对此类平台的 i2i/融合图 API 进行通用实现。
        """
        return {'success': False, 'error_msg': "OpenAI Compatible API (SiliconFlow/RunningHub) fusion/i2i generation not implemented or supported via generic endpoints."}
    
class ComfyUIHandler:
    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        return {'success': False, 'error_msg': "ComfyUI generation not implemented yet"}
    
    @staticmethod
    def fuse_image(prompt, media_manager, config, base_image_path, ref_image_path_list, entity_id=None):
        """
        ComfyUIHandler: 图生图/融合图方法
        ComfyUI 通过工作流可实现强大的 i2i/融合图功能，但这需要解析复杂的工作流 JSON。
        当前实现仅为占位符。
        """
        return {'success': False, 'error_msg': "ComfyUI i2i/fusion generation requires complex workflow logic and is not implemented yet."}
    
class MockHandler:
    @staticmethod
    def generate_text(messages, config): return {'success': True, 'content': "Mock Text Response"}
    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        time.sleep(1)
        mock_url = "https://placehold.co/600x400/2c3e50/ffffff?text=Mock+Image"
        # 即使是Mock，也尝试下载以模拟真实流程
        saved_url = media_manager.download_from_url(mock_url, 'image', entity_id)
        return {'success': True, 'url': saved_url or mock_url}
    @staticmethod
    def generate_video(prompt, media_manager, config, start_img=None, end_img=None, entity_id=None):
        time.sleep(1)
        return {'success': True, 'url': "https://www.w3schools.com/html/mov_bbb.mp4"}
    @staticmethod
    def generate_voice(text, media_manager, config, entity_id=None):
        return {'success': True, 'url': "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"}
    @staticmethod
    def fuse_image(prompt, media_manager, config, base_image_path, ref_image_path_list, entity_id=None):
        time.sleep(1)
        mock_url = "https://placehold.co/600x400/8e44ad/ffffff?text=Mock+Fusion"
        saved_url = media_manager.download_from_url(mock_url, 'image', entity_id)
        return {'success': True, 'url': saved_url or mock_url}

class ViduHandler:
    """
    VIDU API Handler
    支持：
    1. 首尾帧生成视频 (Start-End to Video)
    2. 文生图 / 图生图 (Reference to Image)
    官方文档: https://api.vidu.com/ent/v2/
    """
    
    @staticmethod
    def _get_headers(config):
        return {
            "Authorization": f"Token {config.get('api_key')}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def _wait_for_task(task_id, config, media_manager, media_type, entity_id, max_wait=600):
        base_url = config.get('base_url', 'https://api.vidu.com')
        url = f"{base_url.rstrip('/')}/ent/v2/tasks/{task_id}/creations" 
        headers = ViduHandler._get_headers(config)
        
        logger.info(f"[VIDU] Waiting for task {task_id}...")
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    state = data.get('state')
                    err_code = data.get('err_code')
                    
                    if state == 'success':
                        logger.info(f"[VIDU] Task {task_id} Success.")
                        creations = data.get('creations', [])
                        if creations and len(creations) > 0:
                            result_url = creations[0].get('url')
                            saved_url = media_manager.download_from_url(result_url, media_type, entity_id)
                            logger.info(f"[VIDU] Downloading result from: {result_url}")
                            return {'success': True, 'url': saved_url or result_url}
                    elif state == 'failed':
                        logger.error(f"[VIDU] Task {task_id} Failed. ErrCode: {err_code}")
                        return {'success': False, 'error_msg': f"Failed: {data.get('err_code')}"}
                    time.sleep(5)
                else:
                    logger.warning(f"[VIDU] Unknown state: {state}")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"[VIDU] Query error: {e}")
                time.sleep(5)
        
        return {'success': False, 'error_msg': f'Timeout after {max_wait}s waiting for result'}

    
    @staticmethod
    def generate_video(prompt, media_manager, config, start_img=None, end_img=None, entity_id=None):
        """
        VIDU 首尾帧生成视频 (Start-End to Video)
        必须提供首帧和尾帧
        """
        api_key = config.get('api_key')
        base_url = config.get('base_url', 'https://api.vidu.com')
        model = config.get('model_name', 'viduq2-pro-fast')
        
        if not api_key:
            return {'success': False, 'error_msg': "Missing VIDU API key"}
        
        if not start_img or not end_img:
            return {'success': False, 'error_msg': "VIDU requires both start frame and end frame images"}
        
        
        start_b64 = media_manager.file_to_base64(start_img)
        end_b64 = media_manager.file_to_base64(end_img)
        if not start_b64 or not end_b64: return {'success': False, 'error_msg': "Images required"}
        
        payload = {
            "model": config.get('model_name', 'viduq2-pro-fast'),
            "images": [start_b64, end_b64],
            "prompt": prompt,
            "duration": 2,  # 默认5秒，可根据模型调整
            "resolution": "1080p",  # 默认720p，可选: 540p, 720p, 1080p
            "movement_amplitude": "auto",  # auto, small, medium, large
            "off_peak": False,  # 非高峰模式
            "bgm": False  # 不添加背景音乐
        }
        
        try:
            url = f"{config.get('base_url', 'https://api.vidu.com').rstrip('/')}/ent/v2/start-end2video"
            resp = requests.post(url, json=payload, headers=ViduHandler._get_headers(config), timeout=60)
            
            if resp.status_code in [200, 201]:
                task_id = resp.json().get('task_id')
                return ViduHandler._wait_for_task(task_id, config, media_manager, 'video', entity_id)
            logger.error(f"[VIDU] API Error {resp.status_code}: {resp.text}")
            return {'success': False, 'error_msg': f"API Error {resp.status_code}"}
        except Exception as e:
            logger.exception("[VIDU] Generation failed")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        payload = {
            "model": config.get('model_name', 'viduq2'),
            "images": [],
            "prompt": prompt,
            "aspect_ratio": config.get('aspect_ratio', '16:9'),
            "resolution": config.get('resolution', '1080p'),
        }
        try:
            url = f"{config.get('base_url', 'https://api.vidu.com').rstrip('/')}/ent/v2/reference2image"
            resp = requests.post(url, json=payload, headers=ViduHandler._get_headers(config), timeout=60)
            if resp.status_code in [200, 201]:
                data = resp.json()
                task_id = data.get('task_id')
                state = data.get('state')
                logger.info(f"[VIDU] Image Task created: {task_id}, state: {state}")
                return ViduHandler._wait_for_task(task_id, config, media_manager, 'image', entity_id)
            logger.error(f"[VIDU] API Error {resp.status_code}: {resp.text}")
            return {'success': False, 'error_msg': f"API Error {resp.status_code}"}
        except Exception as e:
            logger.exception("[VIDU] Image generation failed")
            return {'success': False, 'error_msg': str(e)}
    
    @staticmethod
    def generate_text(messages, config):
        """
        VIDU 不支持文本生成，返回错误
        """
        return {'success': False, 'error_msg': "VIDU does not support text generation"}

    @staticmethod
    def fuse_image(prompt, media_manager, config, base_image_path, ref_image_path_list, entity_id=None):
        """
        VIDU 图生图 / Reference to Image
        Endpoint: /ent/v2/reference2image
        Model: viduq2
        """
        api_key = config.get('api_key')
        base_url = config.get('base_url', 'https://api.vidu.com')
        model = config.get('model_name', 'viduq2')
        
        if not api_key:
            return {'success': False, 'error_msg': "Missing VIDU API key"}
        images_payload = []
        
        # 处理 Reference Images
        if ref_image_path_list:
            for p in ref_image_path_list:
                b64 = media_manager.file_to_base64(p)
                if b64: images_payload.append(b64)
        # 处理 Base Image
        if base_image_path:
            b64 = media_manager.file_to_base64(base_image_path)
            if b64: images_payload.append(b64)
        # 检查图片数量限制 (viduq2 supports 0-7)
        if len(images_payload) > 7:
            logger.warning("[VIDU] Too many reference images, truncating to 7")
            images_payload = images_payload[:7]
        payload = {
            "model": config.get('model_name', 'viduq2'),
            "images": images_payload,
            "prompt": prompt,
            "aspect_ratio": config.get('aspect_ratio', '16:9'), # viduq2 supports auto
            "resolution": config.get('resolution', '1080p'),
        }
        try:
            url = f"{config.get('base_url', 'https://api.vidu.com').rstrip('/')}/ent/v2/reference2image"
            resp = requests.post(url, json=payload, headers=ViduHandler._get_headers(config), timeout=60)
            if resp.status_code in [200, 201]:
                data = resp.json()
                task_id = data.get('task_id')
                state = data.get('state')
                logger.info(f"[VIDU] Fusion Task created: {task_id}, state: {state}")
                return ViduHandler._wait_for_task(task_id, config, media_manager, 'image', entity_id)
            logger.error(f"[VIDU] API Error {resp.status_code}: {resp.text}")
            return {'success': False, 'error_msg': f"API Error {resp.status_code}"}
        except Exception as e:
            logger.exception("[VIDU] Fusion generation failed")
            return {'success': False, 'error_msg': str(e)}

class JimengHandler:
    """
    即梦 (Volcengine) API Handler
    支持文生图和首尾帧生视频
    官方文档: https://www.volcengine.com/docs/6791/1160501
    使用火山引擎 V4 签名认证
    
    API Key 格式: AccessKeyId|SecretKey
    例如: AKTP***|YourSecretKey***
    """
    
    # 火山引擎配置常量
    HOST = 'visual.volcengineapi.com'
    REGION = 'cn-north-1'
    ENDPOINT = 'https://visual.volcengineapi.com'
    SERVICE = 'cv'
    METHOD = 'POST'
    
    @staticmethod
    def _parse_credentials(api_key):
        """
        解析凭证
        格式: AccessKeyId|SecretKey
        返回: (access_key, secret_key)
        """
        if not api_key:
            raise ValueError("API Key is required")
        
        if '|' not in api_key:
            raise ValueError("Invalid API Key format. Expected format: AccessKeyId|SecretKey")
        
        parts = api_key.split('|', 1)
        if len(parts) != 2:
            raise ValueError("Invalid API Key format. Expected format: AccessKeyId|SecretKey")
        
        access_key = parts[0].strip()
        secret_key = parts[1].strip()
        
        if not access_key or not secret_key:
            raise ValueError("AccessKeyId and SecretKey cannot be empty")
        
        return access_key, secret_key
    
    @staticmethod
    def _sign(key, msg):
        """HMAC-SHA256 签名"""
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    @staticmethod
    def _get_signature_key(secret_key, date_stamp, region_name, service_name):
        """生成签名密钥"""
        k_date = JimengHandler._sign(secret_key.encode('utf-8'), date_stamp)
        k_region = JimengHandler._sign(k_date, region_name)
        k_service = JimengHandler._sign(k_region, service_name)
        k_signing = JimengHandler._sign(k_service, 'request')
        return k_signing
    
    @staticmethod
    def _format_query(parameters):
        """格式化查询参数"""
        request_parameters_init = ''
        for key in sorted(parameters):
            request_parameters_init += key + '=' + parameters[key] + '&'
        return request_parameters_init[:-1]
    
    @staticmethod
    def _sign_request(access_key, secret_key, req_body, action='CVProcess'):
        """
        火山引擎 V4 签名
        返回 (headers, request_url)
        Updated: 支持自定义 Action 参数 (Action 默认为 CVProcess 以兼容旧接口)
        """
        from datetime import datetime
        
        if not access_key or not secret_key:
            raise ValueError('Missing access_key or secret_key')
        
        # 时间戳
        t = datetime.utcnow()
        current_date = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d')
        
        query_params = {'Action': action, 'Version': '2022-08-31'}
        canonical_querystring = '&'.join([f"{k}={v}" for k,v in sorted(query_params.items())])
        payload_hash = hashlib.sha256(req_body.encode('utf-8')).hexdigest()
        
        signed_headers = 'content-type;host;x-content-sha256;x-date'
        canonical_headers = f'content-type:application/json\nhost:{JimengHandler.HOST}\nx-content-sha256:{payload_hash}\nx-date:{current_date}\n'
        canonical_request = f'{JimengHandler.METHOD}\n/\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        
        credential_scope = f'{datestamp}/{JimengHandler.REGION}/{JimengHandler.SERVICE}/request'
        string_to_sign = f'HMAC-SHA256\n{current_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        
        signing_key = JimengHandler._get_signature_key(secret_key, datestamp, JimengHandler.REGION, JimengHandler.SERVICE)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        headers = {
            'X-Date': current_date,
            'Authorization': f'HMAC-SHA256 Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}',
            'X-Content-Sha256': payload_hash,
            'Content-Type': 'application/json'
        }
        return headers, f'{JimengHandler.ENDPOINT}?{canonical_querystring}'
    
    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        """
        即梦文生图 V3.1 API
        Action: CVSync2AsyncSubmitTask
        """
        api_key_combined = config.get('api_key')
        # 默认模型 V3.1
        model = config.get('model_name', 'jimeng_t2i_v31')
        try:
            access_key, secret_key = JimengHandler._parse_credentials(config.get('api_key'))
        except ValueError as e: return {'success': False, 'error_msg': str(e)}
        
        body_params = {
            "req_key": model, "prompt": prompt, "seed": int(config.get('seed', -1)),
            "use_pre_llm": config.get('use_pre_llm', True)
        }
        
        try:
            req_body = json.dumps(body_params)
            headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body, action='CVSync2AsyncSubmitTask')
            logger.info(f"[Jimeng] Submitting T2I task. Model: {model}, Prompt: {prompt[:30]}...")

            resp = requests.post(request_url, headers=headers, data=req_body, timeout=60)
            if resp.status_code != 200: return {'success': False, 'error_msg': f"Submit failed: {resp.text}"}
            
            data = resp.json()
            if data.get('code') != 10000:
                 return {'success': False, 'error_msg': f"API Error: {data.get('message')}"}
                 
            task_id = data.get('data', {}).get('task_id')
            if not task_id: return {'success': False, 'error_msg': "No task_id returned"}
            
            return JimengHandler._wait_for_t2i_result(task_id, model, access_key, secret_key, media_manager, entity_id)
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def _wait_for_t2i_result(task_id, req_key, access_key, secret_key, media_manager, entity_id, max_wait=600):
        """
        轮询文生图结果
        Action: CVSync2AsyncGetResult
        """
        req_body_str = json.dumps({"req_key": req_key, "task_id": task_id})
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body_str, action='CVSync2AsyncGetResult')
                resp = requests.post(request_url, headers=headers, data=req_body_str, timeout=30)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 10000:
                        status = data.get('data', {}).get('status')
                        logger.info(f"[Jimeng] T2I task {task_id} status: {status}")
                        if status == 'done':
                            logger.info(f"[Jimeng] Task {task_id} Done")
                            image_urls = data['data'].get('image_urls', [])
                            binary = data['data'].get('binary_data_base64', [])
                            
                            if binary:
                                b64_data = base64.b64decode(binary[0])
                                saved_url = media_manager.save_binary(b64_data, 'image', entity_id, '.png')
                                return {'success': True, 'url': saved_url}
                            elif image_urls:
                                saved_url = media_manager.download_from_url(image_urls[0], 'image', entity_id)
                                return {'success': True, 'url': saved_url}
                            return {'success': False, 'error_msg': "No image data returned"}
                        elif status in ['in_queue', 'generating']:
                            time.sleep(2)
                        elif status in ['not_found', 'expired']:
                             logger.warning(f"[Jimeng] Task {task_id} status: {status}")
                             return {'success': False, 'error_msg': f"Task status: {status}"}
                        else:
                            time.sleep(2)
                    else:
                        logger.error(f"[Jimeng] Query Error: {data.get('message')}")
                        return {'success': False, 'error_msg': f"Query failed (code={data.get('code')}): {data.get('message')}"}
                else:
                    logger.warning(f"[Jimeng] Query HTTP Error: {resp.status_code}")
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"[Jimeng] Polling error: {e}")
                time.sleep(2)
                
        return {'success': False, 'error_msg': "Timeout waiting for T2I result"}
    
    @staticmethod
    def generate_video(prompt, media_manager, config, start_img=None, end_img=None, entity_id=None):
        """
        即梦首尾帧生视频 API (Jimeng Video 3.0)
        Action: CVSync2AsyncSubmitTask
        支持 Start-End 模式 (需2张图)
        """
        model = config.get('model_name', 'jimeng_i2v_first_tail_v30_1080')
        try:
            access_key, secret_key = JimengHandler._parse_credentials(config.get('api_key'))
        except ValueError as e: return {'success': False, 'error_msg': str(e)}
        
        # 校验输入
        if not start_img:
            return {'success': False, 'error_msg': "Jimeng video generation requires start frame"}
        img_paths = [start_img]
        if end_img: img_paths.append(end_img)
        images_b64 = []
        for p in img_paths:
            b64 = media_manager.file_to_base64(p)
            if b64 and ',' in b64: images_b64.append(b64.split(',', 1)[1])
            
        body_params = {
            "req_key": model, "binary_data_base64": images_b64,
            "prompt": prompt, "seed": int(config.get('seed', -1)),
            "frames": int(config.get('frames', 121))
        }
        
        try:
            req_body = json.dumps(body_params)
            headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body, action='CVSync2AsyncSubmitTask')
            logger.info(f"[Jimeng] Creating video task with model: {model}")
            resp = requests.post(request_url, headers=headers, data=req_body, timeout=60)
            
            if resp.status_code != 200: return {'success': False, 'error_msg': f"Submit failed: {resp.text}"}
            
            data = resp.json()
            if data.get('code') != 10000:
                 return {'success': False, 'error_msg': f"API Error: {data.get('message')}"}
                 
            task_id = data.get('data', {}).get('task_id')
            if not task_id: return {'success': False, 'error_msg': "No task_id returned"}
            
            logger.info(f"[Jimeng] Video task submitted: {task_id}")
            return JimengHandler._wait_for_video_result(task_id, model, access_key, secret_key, media_manager, entity_id)
        except Exception as e:
            logger.exception("[Jimeng] Video generation failed")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def _wait_for_video_result(task_id, req_key, access_key, secret_key, media_manager, entity_id, max_wait=600):
        """
        轮询视频结果 (Jimeng Video 3.0)
        Action: CVSync2AsyncGetResult
        """
        req_body_str = json.dumps({"req_key": req_key, "task_id": task_id})
        start_time = time.time()
        logger.info(f"[Jimeng] Waiting Video Task {task_id}")
        while time.time() - start_time < max_wait:
            try:
                headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body_str, action='CVSync2AsyncGetResult')
                resp = requests.post(request_url, headers=headers, data=req_body_str, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 10000:
                        status = data['data'].get('status')
                        if status == 'done':
                            video_url = data['data'].get('video_url')
                            if video_url:
                                saved_url = media_manager.download_from_url(video_url, 'video', entity_id)
                                return {'success': True, 'url': saved_url}
                            return {'success': False, 'error_msg': "No video URL"}
                        elif status in ['in_queue', 'generating']:
                            time.sleep(5)
                        else:
                            time.sleep(5)
                    else:
                        # 业务错误 (如审核不通过)
                        logger.error(f"[Jimeng] Query Fail: {data.get('message')}")
                        return {'success': False, 'error_msg': f"Query failed (code={code}): {data.get('message')}"}
                else:
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"[Jimeng] Polling error: {e}")
                time.sleep(5)
                
        return {'success': False, 'error_msg': "Timeout waiting for video result"} 
    
    @staticmethod
    def generate_text(messages, config):
        """
        即梦不支持文本生成
        """
        return {'success': False, 'error_msg': "Jimeng does not support text generation"}

    @staticmethod
    def fuse_image(prompt, media_manager, config, base_image_path, ref_image_path_list, entity_id=None):
        """
        即梦图生图 3.0 (Jimeng Image-to-Image V3.0)
        官方接口: https://visual.volcengineapi.com
        Action: CVSync2AsyncSubmitTask (提交) / CVSync2AsyncGetResult (查询)
        """
        try:
            access_key, secret_key = JimengHandler._parse_credentials(config.get('api_key'))
        except ValueError as e: return {'success': False, 'error_msg': str(e)}

        images_payload = []
        
        # 处理 Reference Images
        if ref_image_path_list:
            for ref_path in ref_image_path_list:
                ref_b64 = media_manager.file_to_base64(ref_path)
                if ref_b64 and ',' in ref_b64: images_payload.append(ref_b64.split(',', 1)[1])
        
        
        # 准备图片 Base64
        # 注意: 接口需要纯 base64 字符串，不包含 "data:image/png;base64," 前缀
        img_b64 = media_manager.file_to_base64(base_image_path)
        if img_b64 and ',' in img_b64: images_payload.append(img_b64.split(',', 1)[1])
        else: return {'success': False, 'error_msg': f"Failed to encode base image"}

        req_payload = {
            "req_key": "jimeng_i2i_v30", "binary_data_base64": images_payload,
            "prompt": prompt, "seed": int(config.get('seed', -1)), "scale": float(config.get('scale', 0.5)),
        }
        
        try:
            req_body_str = json.dumps(req_payload)
            headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body_str, action='CVSync2AsyncSubmitTask')
            
            logger.info(f"[Jimeng] Submitting i2i task. Prompt: {prompt[:30]}...")
            resp = requests.post(request_url, headers=headers, data=req_body_str, timeout=60)
            
            if resp.status_code != 200: return {'success': False, 'error_msg': f"Submit failed: {resp.text}"}
            
            data = resp.json()
            task_id = data.get('data', {}).get('task_id')
            if not task_id: return {'success': False, 'error_msg': "No task_id returned"}
            
            logger.info(f"[Jimeng] i2i task submitted. Task ID: {task_id}")
            return JimengHandler._wait_for_i2i_result(task_id, access_key, secret_key, media_manager, entity_id)
        except Exception as e:
            logger.exception("[Jimeng] Fusion failed")
            return {'success': False, 'error_msg': str(e)}
            
    @staticmethod
    def _wait_for_i2i_result(task_id, access_key, secret_key, media_manager, entity_id, max_wait=600):
        """
        轮询图生图结果
        """
        req_body_str = json.dumps({"req_key": "jimeng_i2i_v30", "task_id": task_id})
        start_time = time.time()
        
        logger.info(f"[Jimeng] Waiting i2i Task {task_id}")
        while time.time() - start_time < max_wait:
            try:
                headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body_str, action='CVSync2AsyncGetResult')
                resp = requests.post(request_url, headers=headers, data=req_body_str, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 10000:
                        status = data['data'].get('status')
                        logger.info(f"[Jimeng] i2i task {task_id} status: {status}")
                        if status == 'done':
                            image_urls = data['data'].get('image_urls', [])
                            binary = data['data'].get('binary_data_base64', [])
                            
                            if binary:
                                b64_data = base64.b64decode(binary[0])
                                saved_url = media_manager.save_binary(b64_data, 'image', entity_id, '.png')
                                return {'success': True, 'url': saved_url}
                            elif image_urls:
                                saved_url = media_manager.download_from_url(image_urls[0], 'image', entity_id)
                                return {'success': True, 'url': saved_url}
                            return {'success': False, 'error_msg': "No data"}
                        elif status in ['in_queue', 'generating']:
                            time.sleep(2)
                        else:
                             time.sleep(2)
                    else:
                        time.sleep(2)
                else:
                    logger.warning(f"[Jimeng] Query HTTP Error: {resp.status_code}")
                    time.sleep(2)

            except Exception as e:
                logger.error(f"[Jimeng] Polling error: {e}")
                time.sleep(2)
        
        return {'success': False, 'error_msg': "Timeout waiting for i2i result"}


class MiniMaxHandler:
    @staticmethod
    def _get_headers(config):
        return {"Authorization": f"Bearer {config.get('api_key')}", "Content-Type": "application/json"}

    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        """
        MiniMax 文生图 API
        官方文档: https://platform.minimaxi.com/docs/api-reference/image/generation/api/text-to-image
        """
        api_key = config.get('api_key')
        model = config.get('model_name', 'image-01')
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        
        payload = {"model": model, "prompt": prompt, "response_format": "url", "n": 1}
        # 添加其他可选参数
        if config.get('seed') is not None:
            payload["seed"] = config.get('seed')
        if config.get('prompt_optimizer') is not None:
            payload["prompt_optimizer"] = config.get('prompt_optimizer', True)
        if config.get('aigc_watermark') is not None:
            payload["aigc_watermark"] = config.get('aigc_watermark', False)
        
        try:
            url = f"{base_url.rstrip('/')}/v1/image_generation"
            resp = requests.post(url, json=payload, headers=MiniMaxHandler._get_headers(config), timeout=120)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('base_resp', {}).get('status_code') == 0:
                    img_url = data['data']['image_urls'][0]
                    saved_url = media_manager.download_from_url(img_url, 'image', entity_id)
                    return {'success': True, 'url': saved_url or img_url}
                return {'success': False, 'error_msg': f"API Error: {data.get('base_resp', {}).get('status_msg')}"}
            
            return {'success': False, 'error_msg': f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}
    
    @staticmethod
    def generate_text(messages, config): return {'success': False, 'error_msg': "MiniMax does not support text generation"}
    
    @staticmethod
    def generate_video(prompt, media_manager, config, start_img=None, end_img=None, entity_id=None):
        """
        MiniMax 首尾帧生成视频 API
        官方文档: https://platform.minimaxi.com/docs/api-reference/video/generation/api/start-end-to-video
        """
        api_key = config.get('api_key')
        model = config.get('model_name', 'MiniMax-Hailuo-02')
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        
        start_b64 = media_manager.file_to_base64(start_img)
        end_b64 = media_manager.file_to_base64(end_img)
        if not start_b64 or not end_b64: return {'success': False, 'error_msg': "Failed to encode images"}
        
        payload = {
            "model": model, "first_frame_image": start_b64, "last_frame_image": end_b64,
            "prompt": prompt, "prompt_optimizer": config.get('prompt_optimizer', True),
            "duration": config.get('duration', 6),
            "resolution": config.get('resolution', '768P')
        }
        
        try:
            url = f"{base_url.rstrip('/')}/v1/video_generation"
            resp = requests.post(url, json=payload, headers=MiniMaxHandler._get_headers(config), timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('base_resp', {}).get('status_code') == 0:
                    task_id = data.get('task_id')
                    result = MiniMaxHandler._wait_for_video(task_id, config, max_wait=600)
                    if result['success'] and result.get('url'):
                        saved_url = media_manager.download_from_url(result['url'], 'video', entity_id)
                        return {'success': True, 'url': saved_url or result['url']}
                    return result
                logger.error(f"[MiniMax] API Error {data.get('base_resp', {}).get('status_code')}: {data.get('base_resp', {}).get('status_msg')}")
                return {'success': False, 'error_msg': f"API Error: {data.get('base_resp', {}).get('status_msg')}"}
            
            return {'success': False, 'error_msg': f"HTTP {resp.status_code}"}
        
        except requests.exceptions.Timeout:
            return {'success': False, 'error_msg': 'Request timeout'}
        except Exception as e:
            logger.exception("[MiniMax] Video generation failed")
            return {'success': False, 'error_msg': str(e)}
    
    @staticmethod
    def _wait_for_video(task_id, config, max_wait=600):
        """
        轮询等待视频生成完成
        max_wait: 最大等待时间(秒)
        """
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        url = f"{base_url.rstrip('/')}/v1/query/video_generation?task_id={task_id}"
        headers = MiniMaxHandler._get_headers(config)
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('base_resp', {}).get('status_code') == 0:
                        status = data.get('status')
                        if status == 'Success':
                            return {'success': True, 'url': data.get('video_url')}
                        elif status == 'Failed':
                            return {'success': False, 'error_msg': data.get('error_message')}
                        else:
                            time.sleep(10)
                    else:
                        time.sleep(10)
                else:
                    time.sleep(10)
            except Exception:
                time.sleep(10)
        return {'success': False, 'error_msg': 'Timeout'}

    @staticmethod
    def fuse_image(prompt, media_manager, config, base_image_path, ref_image_path_list, entity_id=None):
        api_key = config.get('api_key')
        model = config.get('model_name', 'image-01')
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        
        ref_image_path_list.append(base_image_path)
        subject_references = []
        for image_path in ref_image_path_list:
            image_b64 = media_manager.file_to_base64(image_path)
            if image_b64: subject_references.append({"type": "character", "image_file": image_b64})
        
        payload = {
            "model": model, "prompt": prompt, "subject_reference": subject_references,
            "response_format": "url", "n": 1
        }
        
        try:
            url = f"{base_url.rstrip('/')}/v1/image_generation"
            resp = requests.post(url, json=payload, headers=MiniMaxHandler._get_headers(config), timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('base_resp', {}).get('status_code') == 0:
                    img_url = data['data']['image_urls'][0]
                    saved_url = media_manager.download_from_url(img_url, 'image', entity_id)
                    return {'success': True, 'url': saved_url or img_url}
                return {'success': False, 'error_msg': f"API Error: {data}"}
            return {'success': False, 'error_msg': f"HTTP {resp.status_code}"}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

class ZhipuHandler:
    @staticmethod
    def generate_text(messages, config):
        try:
            api_key = config.get('api_key')
            model = config.get('model_name') or 'glm-4.6'
            client = ZhipuAiClient(api_key=api_key)
            
            response = client.chat.completions.create(model=model, messages=messages)
            if response.choices:
                return {'success': True, 'content': response.choices[0].message.content}
            return {'success': False, 'error_msg': "No response"}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_image(prompt, media_manager, config, entity_id=None):
        try:
            api_key = config.get('api_key')
            model = config.get('model_name') or 'cogview-3'
            client = ZhipuAiClient(api_key=api_key)
            
            response = client.images.generations(
                model=model, prompt=prompt,
                size=config.get('size', "1024x1024"),
                quality=config.get('quality', "standard")
            )
            
            if response.data:
                img_url = response.data[0].url
                saved_url = media_manager.download_from_url(img_url, 'image', entity_id)
                return {'success': True, 'url': saved_url or img_url}
            return {'success': False, 'error_msg': "No image data"}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_video(prompt, media_manager, config, start_img=None, end_img=None, entity_id=None):
        try:
            api_key = config.get('api_key')
            start_img_b64 = media_manager.file_to_base64(start_img)
            end_img_b64 = media_manager.file_to_base64(end_img)
            if not start_img_b64: return {'success': False, 'error_msg': "Zhipu requires start image"}
            
            model = config.get('model_name') or 'cogvideox-2'
            client = ZhipuAiClient(api_key=api_key)
            
            response = client.videos.generations(
                model=model, image_url=[start_img_b64, end_img_b64] if end_img_b64 else [start_img_b64],
                prompt=prompt, quality=config.get('quality', "speed"),
                with_audio=config.get('with_audio', True)
            )
            
            max_wait = config.get('max_wait', 600)
            start_time = time.time()
            while time.time() - start_time < max_wait:
                result = client.videos.retrieve_videos_result(id=response.id)
                if result.status == 'succeeded':
                    video_url = result.data[0].url if result.data else None
                    if video_url:
                        saved_url = media_manager.download_from_url(video_url, 'video', entity_id)
                        return {'success': True, 'url': saved_url or video_url}
                elif result.status == 'failed':
                    return {'success': False, 'error_msg': str(result.failure_details)}
                time.sleep(10)
            return {'success': False, 'error_msg': "Timeout"}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def fuse_image(prompt, media_manager, config, base_image_path, ref_image_path_list, entity_id=None):
        return {'success': False, 'error_msg': "智谱目前无提供融合图模型"}
    
# ============================================================
#  Dispatcher
# ============================================================

def get_handler(provider_type):
    if provider_type == 'aliyun': return AliyunHandler
    if provider_type == 'siliconflow' or provider_type == 'runninghub': return OpenAICompatibleHandler
    if provider_type == 'comfyui': return ComfyUIHandler
    if provider_type == 'vidu': return ViduHandler
    if provider_type == 'jimeng': return JimengHandler
    if provider_type == 'zai': return ZhipuHandler
    if provider_type == 'minimax': return MiniMaxHandler
    return MockHandler

# ============================================================
#  Business Logic (Prompt Engineering & Coordination)
# ============================================================

def run_text_generation(messages, config):
    logger.info(f"[Main] Run Text Gen. Provider: {config.get('type')}")
    handler = get_handler(config.get('type'))
    return handler.generate_text(messages, config)


def run_image_generation(visual_desc, style_desc, consistency_text, frame_type, config, media_manager, start_prompt_ref=None, prev_shot_context="", entity_id=None):
    """
    图片生成流程：包含 Prompt 优化逻辑 (Prompt Chaining)

    此方法是生成电影/短剧分镜图片的核心入口。它首先利用大型语言模型（LLM）进行
    Prompt 工程（提示词优化），然后调用相应的图像生成 API Handler。
    该方法实现了连续镜头中“起始帧”和“结束帧”提示词的精准生成与控制。

    Args:
        visual_desc (str): 画面内容的描述。
            - 如果 frame_type='start'，这是起始帧的主体和动作描述。
            - 如果 frame_type='end'，这是结束帧的新动作描述。
        style_desc (str): 画面风格的描述（仅在 frame_type='start' 时使用）。
        consistency_text (str): 跨镜头一致性描述（如人物、环境、核心氛围）。
        frame_type (str): 帧类型，必须是 'start' (起始帧) 或 'end' (结束帧)。
        config (Dict[str, Any]): AI 服务配置字典，用于图像生成 API，包含：
            - 'type' (str): 服务提供商类型，例如 'aliyun', 'siliconflow', 'zai'。
            - 'api_key' (str): API 密钥。
            - 'model_name' (str, optional): 图像生成模型名称。
            - (LLM 降级配置): 内部会尝试将 'model_name' 替换为适用的文本模型（如 'qwen-plus'）进行 Prompt 优化。
        save_dir (str): 生成的图片文件存储的本地目录路径。
        url_prefix (str): 访问生成的图片文件时使用的 URL 前缀。
        start_prompt_ref (Optional[str]): **仅当 frame_type='end' 时需要。**
                                          这是由 LLM 为起始帧生成的**优化后**提示词，用于确保结束帧在风格和运镜上100%匹配。
        prev_shot_context (str): 前一个镜头的简短上下文描述，用于辅助 LLM 在生成起始帧时保持叙事连贯性。

    Returns:
        Tuple[Dict[str, Any], str]: 包含两部分的元组：
            - Dict[str, Any]: 图像生成 API 的结果字典（'success', 'url', 'error_msg'）。
            - str: 最终用于图像生成器（如 Midjourney、Stable Diffusion）的**优化后的**完整 Prompt 文本。
    """
    logger.info(f"[Main] Run Image Gen. Provider: {config.get('type')}, FrameType: {frame_type}")

    # 1. 准备 Prompt Engineering 的输入
    consistency_instruction = f"**GLOBAL VISUAL RULES**: {consistency_text}. Maintain consistent characters and environment.\n" if consistency_text else ""
    context_instruction = f"\n**PREVIOUS SHOT CONTEXT**: \"{prev_shot_context}\". Ensure narrative continuity." if prev_shot_context else ""

    sys_prompt = ""
    user_prompt = ""

    if frame_type == 'start':
        sys_prompt = f"""你是一位专业的AI电影分镜提示词工程师。专为电影/短剧的连续镜头生成【起始帧分镜】提示词。{consistency_instruction}{context_instruction} 核心要求：
    1. 完整描述主体、环境、光线、构图、风格（含笔触、色彩、光影、质感、渲染方式）；
    2. 严格遵循电影分镜规范：无任何商业水印、无宣传文案/标语、无海报式排版、无装饰性边框，仅呈现纯分镜画面；
    3. 明确标注摄影机参数（机位、视角、焦距、景别、机位高度、轴线方向），且所有参数需符合电影连续镜头拍摄逻辑；
    4. 所有风格/摄影参数需具备可复用性，确保后续基于此生成的结束帧能完全匹配，符合连续镜头的视觉一致性；
    5. 输出的提示词仅用于生成电影/短剧分镜帧，非单张宣传图/海报/装饰画；
    6. 使用中文，逗号分隔，仅直接输出提示词文本，无额外说明。"""
        user_prompt = f"风格：{style_desc}\n描述：{visual_desc}\n核心约束：生成结果为电影/短剧的起始分镜帧，无水印、无宣传文案、无海报风格，仅为纯分镜画面；明确标注摄影机机位/视角/焦距/景别/高度/轴线方向（遵循180度轴线规则），风格特征需具体到笔触/色彩/光影/质感/渲染方式，确保可精准复用于后续结束帧生成。"
    else:
        sys_prompt = f"""你是一位专业的AI电影分镜提示词工程师。基于【起始帧分镜提示词】生成电影/短剧的【结束帧分镜】提示词。{consistency_instruction} 核心要求：
    1. **严格保持**起始帧提示词中的所有核心特征100%不变（禁止任何偏离）：
    - 风格类：人物外貌、背景、笔触、色彩、光影、质感、渲染方式；
    - 摄影类：摄影机机位、视角、焦距、景别、机位高度、轴线方向（严格遵守180度轴线规则，禁止越轴）；
    - 分镜属性：无水印、无宣传文案、无海报式排版、纯分镜画面的核心属性；
    2. **仅修改**基于「结束帧描述」的人物动作/姿势，且动作修改需符合原有摄影机视角和轴线逻辑，适配连续镜头的分镜节奏；
    3. 输出的提示词仅用于生成电影/短剧的结束分镜帧，非单张宣传图/海报/装饰画，需保持与起始帧的连续镜头一致性；
    4. 使用中文，仅直接输出提示词文本，无额外说明。"""
        user_prompt = f"起始帧提示词：{start_prompt_ref}\n\n结束帧动作：{visual_desc}\n\n强制约束：生成结果为电影/短剧的结束分镜帧，无水印、无宣传文案、无海报风格，仅为纯分镜画面；禁止修改起始帧的画风（笔触/色彩/光影/质感/渲染方式）、摄影机参数（机位/视角/焦距/景别/高度/轴线），仅调整人物动作/姿势，且动作需符合连续镜头的分镜逻辑，严格遵守180度轴线规则。"   
    
    optimized_prompt = f"{style_desc}, {visual_desc}" 
    if consistency_text: optimized_prompt += f", {consistency_text}"

    # 2. 尝试使用文本模型优化 Prompt
    handler = get_handler('aliyun')
    if hasattr(handler, 'generate_text'):
        try:
            text_config = config.copy()
            if config.get('type') == 'aliyun': text_config['model_name'] = 'qwen-plus'
            elif config.get('type') in ['siliconflow', 'runninghub']: text_config['model_name'] = 'Qwen/Qwen2.5-7B-Instruct'
            elif config.get('type') == 'zai': text_config['model_name'] = 'glm-4.6'
            
            logger.info("[Prompt Eng] Starting optimization...")
            res = handler.generate_text([{'role': 'system', 'content': sys_prompt + " 使用中文回答"}, {'role': 'user', 'content': user_prompt}], text_config)
            
            if res['success']:
                optimized_prompt = res['content']
                logger.info(f"[Prompt Eng] Optimized: {optimized_prompt[:50]}...")
            else:
                logger.warning(f"[Prompt Eng] Failed: {res.get('error_msg')}")
        except Exception as e:
            logger.error(f"[Prompt Eng] Error: {e}")

    # Call actual image generation with version control
    img_handler = get_handler(config.get('type'))
    result = img_handler.generate_image(optimized_prompt, media_manager, config, entity_id)
    
    return result, optimized_prompt

def run_video_generation(prompt, start_img_path, end_img_path, config, media_manager, entity_id=None):
    """
    视频生成逻辑入口 (Video Generation Entry Point)

    此方法根据配置的提供商类型，调用相应的 Handler 来执行“文生视频”或“首尾帧生视频”操作。
    它负责将用户输入、文件路径和配置传递给具体的 AI 服务实现（如 AliyunHandler, ViduHandler, MiniMaxHandler 等）。

    Args:
        prompt (str): 用于指导视频内容和风格的文本提示词。
        start_img_path (str): 视频起始帧图片的本地文件路径。
                              注意：部分提供商（如 Jimeng, MiniMax, Zhipu, Vidu）要求此参数。
        end_img_path (str): 视频结束帧图片的本地文件路径。
                            注意：部分提供商（如 Vidu, MiniMax, Zhipu）要求此参数，而其他提供商可能忽略。
        config (Dict[str, Any]): AI 服务配置字典，包含以下关键信息：
            - 'type' (str): 服务提供商类型，例如 'aliyun', 'vidu', 'minimax', 'jimeng', 'zai'。
            - 'api_key' (str): API 密钥或凭证。
            - 'model_name' (str, optional): 使用的模型名称。例如 'wanx2.1-kf2v-plus' (Aliyun)。
            - 'base_url' (str, optional): API 基础 URL (如果不是默认值)。
            - (视频特有参数，根据提供商不同):
                - 'duration' (int, optional): 视频时长（秒）。
                - 'resolution' (str, optional): 视频分辨率（如 '720P', '1080P'）。
                - 'max_wait' (int, optional): 轮询等待任务完成的最大时间（秒）。
        save_dir (str): 生成的视频文件存储的本地目录路径。
        url_prefix (str): 访问生成的视频文件时使用的 URL 前缀。

    Returns:
        Dict[str, Any]: 包含生成结果的字典：
            - 'success' (bool): 操作是否成功。
            - 'url' (str, optional): 生成视频文件的公开访问 URL。
            - 'error_msg' (str, optional): 错误信息（如果 'success' 为 False）。
    """
    logger.info(f"[Main] Run Video Gen. Provider: {config.get('type')}, EntityID: {entity_id}")
    handler = get_handler(config.get('type'))
    return handler.generate_video(prompt, media_manager, config, start_img=start_img_path, end_img=end_img_path, entity_id=entity_id)

def run_simple_image_generation(prompt, config, media_manager, entity_id=None):
    """
    不带提示词工程的简单图片生成方法
    直接使用用户提供的prompt，不进行任何优化
    """
    logger.info(f"[Main] Run Simple Image Gen. Provider: {config.get('type')}, EntityID: {entity_id}")
    handler = get_handler(config.get('type', 'mock'))
    return handler.generate_image(prompt, media_manager, config, entity_id)

def run_voice_generation(text, config, media_manager, entity_id=None):
    logger.info(f"[Main] Run Voice Gen. Provider: {config.get('type')}, EntityID: {entity_id}")
    handler = get_handler(config.get('type'))
    return handler.generate_voice(text, media_manager, config, entity_id)

def run_fusion_generation(base_image_path, fusion_prompt, config, media_manager, element_image_paths, entity_id=None):
    """
    融图/图生图逻辑入口 (Image Fusion / Image-to-Image Generation)

    此方法根据配置的提供商类型，调用相应的 Handler 来执行图片融合或图生图操作。
    它主要用于需要一张基础图和/或多张参考图来生成新图片的场景（例如，MiniMax 的角色图生图）。

    Args:
        base_image_path (str): 基础图片的文件路径。在 MiniMax 角色图生图场景中，它被视为一个额外的角色参考图。
        fusion_prompt (str): 用于指导图片生成或融合的文本提示词。
        config (Dict[str, Any]): AI 服务配置字典，包含以下关键信息：
            - 'type' (str): 服务提供商类型，例如 'minimax'。
            - 'api_key' (str): API 密钥。
            - 'model_name' (str, optional): 使用的模型名称。例如 'image-01' (MiniMax)。
            - 'base_url' (str, optional): API 基础 URL (如果不是默认值)。
            - 'aspect_ratio' (str, optional): 图像的宽高比（如 '16:9'）。
            - 'width' (int, optional): 图像宽度（像素）。
            - 'height' (int, optional): 图像高度（像素）。
            - (MiniMax 特有):
                - 'prompt_optimizer' (bool, optional): 是否启用 Prompt 优化 (默认为 True)。
                - 'aigc_watermark' (bool, optional): 是否添加 AIGC 水印。
                - 'seed' (int, optional): 随机种子，用于复现结果。
                - 'style_type' (str, optional): 风格类型（仅部分模型如 'image-01-live' 有效）。
                - 'style_weight' (float, optional): 风格权重。
        save_dir (str): 生成的图片文件存储的本地目录路径。
        url_prefix (str): 访问生成的图片文件时使用的 URL 前缀。
        element_image_paths (List[str]): 额外的元素/参考图片文件路径列表（例如，在 MiniMax 中作为其他角色参考）。

    Returns:
        Dict[str, Any]: 包含生成结果的字典：
            - 'success' (bool): 操作是否成功。
            - 'url' (str, optional): 生成图片的公开访问 URL。
            - 'error_msg' (str, optional): 错误信息（如果 'success' 为 False）。
    """
    logger.info(f"[Main] Run Fusion Gen. Provider: {config.get('type')}, EntityID: {entity_id}")
    handler = get_handler(config.get('type', 'mock'))
    return handler.fuse_image(fusion_prompt, media_manager, config, base_image_path, ref_image_path_list=element_image_paths, entity_id=entity_id)