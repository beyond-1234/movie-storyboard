import os
import requests
import time
import json
import base64
import mimetypes
import logging
import random
import uuid
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath, Path
from typing import Dict, Any, Optional, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AIService")

# 尝试导入 dashscope
try:
    import dashscope
    from dashscope import ImageSynthesis, VideoSynthesis, MultiModalConversation, Generation
    # 引入语音合成模块
    from dashscope.audio.tts import SpeechSynthesizer 
    logger.info("DashScope SDK imported successfully.")
except ImportError:
    dashscope = None
    logger.warning("Warning: 'dashscope' library not found. AI features will fail.")

def file_to_base64(file_path: str) -> Optional[str]:
    """
    将本地文件转换为 Base64 Data URI 格式
    """
    logger.debug(f"[Base64] Converting file: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"[Base64] File not found: {file_path}")
        return None
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'image/png'
        logger.warning(f"[Base64] Could not guess mime type, defaulting to {mime_type}")
        
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
            base64_data = base64.b64encode(file_content).decode('utf-8')
        
        result = f"data:{mime_type};base64,{base64_data}"
        logger.info(f"[Base64] Conversion successful. Type: {mime_type}, Size: {len(file_content)} bytes")
        return result
    except Exception as e:
        logger.error(f"[Base64] Conversion failed for {file_path}: {e}", exc_info=True)
        return None

def generate_aliyun_text(
    messages: List[Dict[str, str]],
    api_key: Optional[str] = None,
    model: str = "qwen-plus"
) -> Dict[str, Any]:
    """调用通义千问进行文本生成"""
    logger.info(f"[Text Gen] Request received. Model: {model}")
    if not dashscope: return {'success': False, 'error_msg': '服务器缺少 dashscope 依赖库', 'status_code': 500}
    final_api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
    if not final_api_key: return {'success': False, 'error_msg': '未配置 DASHSCOPE_API_KEY', 'status_code': 401}

    try:
        response = Generation.call(api_key=final_api_key, model=model, messages=messages, result_format='message')
        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            return {'success': True, 'content': content}
        else:
            err_msg = f"API Error: {response.code} - {response.message}"
            logger.error(f"[Text Gen] {err_msg}")
            return {'success': False, 'error_msg': err_msg, 'status_code': response.status_code}
    except Exception as e:
        logger.exception(f"[Text Gen] Exception: {e}")
        return {'success': False, 'error_msg': str(e), 'status_code': 500}

def generate_aliyun_image(
    prompt: str, 
    save_dir: str, 
    url_prefix: str, 
    api_key: Optional[str] = None,
    model: str = "qwen-image-plus", 
    endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """调用阿里云通义万相/Qwen-VL API 生成图片并保存到本地"""
    logger.info(f"[Image Gen] Request received. Model: {model}")
    if not dashscope: return {'success': False, 'error_msg': '服务器缺少 dashscope 依赖库', 'status_code': 500}
    final_api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
    if not final_api_key: return {'success': False, 'error_msg': '未配置 DASHSCOPE_API_KEY', 'status_code': 401}
    
    if endpoint and endpoint.strip(): 
        dashscope.base_http_api_url = endpoint
        logger.info(f'[Image Gen] Using Custom Endpoint: {endpoint}')

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    messages = [{"role": "user", "content": [{"text": prompt}]}]

    try:
        logger.info(f'[Image Gen] Calling API... Prompt: {prompt[:50]}...')
        kwargs = { "api_key": final_api_key, "model": model, "messages": messages, "result_format": 'message', "stream": False, "prompt_extend": True }
        rsp = MultiModalConversation.call(**kwargs)
        logger.info(f"[Image Gen] API Response Status: {rsp.status_code}")

        if rsp.status_code == HTTPStatus.OK:
            img_url = None
            try:
                content_list = rsp.output.choices[0].message.content
                for item in content_list:
                    if 'image' in item: img_url = item['image']; break
            except Exception as e: logger.error(f"[Image Gen] Parse failed: {e}"); return {'success': False, 'error_msg': '解析失败', 'status_code': 500}
            
            if not img_url: return {'success': False, 'error_msg': '未包含图片URL', 'status_code': 500}
            
            file_name = PurePosixPath(unquote(urlparse(img_url).path)).parts[-1]
            if not file_name.endswith(('.png', '.jpg', '.jpeg', '.webp')): file_name += ".png"
            save_path = Path(save_dir) / file_name
            image_content = requests.get(img_url, timeout=60).content
            with open(save_path, 'wb+') as f: f.write(image_content)
            
            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{file_name}"}
        else:
            return {'success': False, 'error_msg': f'{rsp.code}: {rsp.message}', 'status_code': rsp.status_code}
    except Exception as e:
        logger.exception(f'[Image Gen] Exception: {e}')
        return {'success': False, 'error_msg': str(e), 'status_code': 500}

def generate_aliyun_video(
    prompt: str,
    save_dir: str,
    url_prefix: str,
    api_key: Optional[str] = None,
    model: str = "wanx2.1-kf2v-plus",
    endpoint: Optional[str] = None,
    start_img_path: Optional[str] = None,
    end_img_path: Optional[str] = None
) -> Dict[str, Any]:
    """同步调用阿里云视频生成 API"""
    logger.info(f"[Video Gen] Request received. Model: {model}")
    if not dashscope: return {'success': False, 'error_msg': '服务器缺少 dashscope 依赖库', 'status_code': 500}
    final_api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
    if not final_api_key: return {'success': False, 'error_msg': '未配置 DASHSCOPE_API_KEY', 'status_code': 401}
    
    if endpoint and endpoint.strip(): 
        dashscope.base_http_api_url = endpoint
        logger.info(f'[Video Gen] Using Custom Endpoint: {endpoint}')
    
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    try:
        input_params = {'model': model, 'prompt': prompt, 'prompt_extend': True}
        if start_img_path: 
            b64 = file_to_base64(start_img_path)
            if b64: input_params['first_frame_url'] = b64
        if end_img_path: 
            b64 = file_to_base64(end_img_path)
            if b64: input_params['last_frame_url'] = b64

        logger.info(f"[Video Gen] Calling Sync API...")
        rsp = VideoSynthesis.call(api_key=final_api_key, **input_params)

        if rsp.status_code == HTTPStatus.OK:
            video_url = rsp.output.video_url
            file_name = f"{rsp.output.task_id}.mp4"
            save_path = Path(save_dir) / file_name
            logger.info(f'[Video Gen] Downloading to {save_path}...')
            with open(save_path, 'wb+') as f: f.write(requests.get(video_url, timeout=300).content)
            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{file_name}"}
        else:
            return {'success': False, 'error_msg': f'{rsp.code}: {rsp.message}', 'status_code': rsp.status_code}
    except Exception as e:
        logger.exception(f'[Video Gen] Exception: {e}')
        return {'success': False, 'error_msg': str(e), 'status_code': 500}

def generate_aliyun_voiceover(
    text: str,
    save_dir: str,
    url_prefix: str,
    api_key: Optional[str] = None,
    model: str = "qwen-tts", # Updated model
    voice: str = "Cherry",
    endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    调用阿里云通义千问语音生成模型
    使用 SpeechSynthesizer.call 接口
    """
    logger.info(f"[Voice Gen] Request received. Model: {model}, Voice: {voice}")

    if not dashscope:
        return {'success': False, 'error_msg': '服务器缺少 dashscope 依赖库', 'status_code': 500}

    final_api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
    if not final_api_key:
        return {'success': False, 'error_msg': '未配置 DASHSCOPE_API_KEY', 'status_code': 401}

    if endpoint and endpoint.strip(): 
        dashscope.base_http_api_url = endpoint
        logger.info(f'[Voice Gen] Using Custom Endpoint: {endpoint}')

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f'[Voice Gen] Calling API... Text: {text[:50]}...')
        
        # 使用 SpeechSynthesizer 调用
        result = SpeechSynthesizer.call(
            model=model,
            api_key=final_api_key,
            text=text,
            voice=voice,
            format='mp3' # 明确指定格式
        )
        
        # 严格检查状态码
        if result.status_code == HTTPStatus.OK:
            # 只有成功时，result 才是 SpeechSynthesisResult，才有 get_audio_data
            audio_data = None
            if hasattr(result, 'get_audio_data'):
                audio_data = result.get_audio_data()
            
            if audio_data:
                file_name = f"{uuid.uuid4()}.mp3"
                save_path = Path(save_dir) / file_name
                
                with open(save_path, 'wb') as f:
                    f.write(audio_data)
                    
                web_url = f"{url_prefix.rstrip('/')}/{file_name}"
                logger.info(f'[Voice Gen] Success. Web URL: {web_url}')
                return {'success': True, 'url': web_url}
            else:
                logger.error(f"[Voice Gen] API returned OK but no audio data.")
                return {'success': False, 'error_msg': 'No audio data received', 'status_code': 500}
        else:
            # 失败情况 result 可能是 DashScopeResponse
            err_code = getattr(result, 'code', 'Unknown')
            err_msg = getattr(result, 'message', 'Unknown Error')
            logger.error(f"[Voice Gen] API Failed: {err_code} - {err_msg}")
            return {'success': False, 'error_msg': f"{err_code}: {err_msg}", 'status_code': result.status_code}

    except Exception as e:
        logger.exception(f'[Voice Gen] Exception: {e}')
        return {'success': False, 'error_msg': str(e), 'status_code': 500}