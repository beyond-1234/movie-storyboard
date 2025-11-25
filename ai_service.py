import os
import time
import json
import base64
import mimetypes
import logging
import requests
import uuid
import random
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath, Path
from typing import Dict, Any, Optional, List

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

def file_to_base64(file_path: str) -> Optional[str]:
    if not file_path or not os.path.exists(file_path): return None
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type: mime_type = 'image/png'
    try:
        with open(file_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
    except Exception as e:
        logger.error(f"[Base64] Error: {e}")
        return None

def download_file(url: str, save_path: str):
    try:
        resp = requests.get(url, stream=True, timeout=120)
        if resp.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(1024): f.write(chunk)
            return True
        else:
            logger.error(f"Download returned status {resp.status_code}")
    except Exception as e:
        logger.error(f"Download failed: {e}")
    return False

# ============================================================
#  Provider Handlers (不同提供商的实现)
# ============================================================

class AliyunHandler:
    @staticmethod
    def generate_text(messages, config):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key') or os.getenv("DASHSCOPE_API_KEY")
        model = config.get('model_name') or 'qwen-plus'
        
        try:
            rsp = Generation.call(api_key=api_key, model=model, messages=messages, result_format='message')
            if rsp.status_code == HTTPStatus.OK:
                return {'success': True, 'content': rsp.output.choices[0].message.content}
            return {'success': False, 'error_msg': rsp.message}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key')
        model = config.get('model_name') or 'qwen-image-plus'
        
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
                        fname = f"{uuid.uuid4()}.png"
                        save_path = os.path.join(save_dir, fname)
                        if download_file(img_url, save_path):
                            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                except Exception as e:
                    return {'success': False, 'error_msg': f"Parse failed: {e}"}
            return {'success': False, 'error_msg': getattr(rsp, 'message', 'Unknown Error')}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_video(prompt, save_dir, url_prefix, config, start_img=None, end_img=None):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key')
        model = config.get('model_name') or 'wanx2.1-kf2v-plus'
        
        params = {'model': model, 'prompt': prompt, 'prompt_extend': True}
        if start_img: 
            b64 = file_to_base64(start_img)
            if b64: params['first_frame_url'] = b64
        if end_img: 
            b64 = file_to_base64(end_img)
            if b64: params['last_frame_url'] = b64
        
        try:
            rsp = VideoSynthesis.call(api_key=api_key, **params)
            if rsp.status_code == HTTPStatus.OK:
                video_url = rsp.output.video_url
                fname = f"{rsp.output.task_id}.mp4"
                save_path = os.path.join(save_dir, fname)
                if download_file(video_url, save_path):
                    return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
            return {'success': False, 'error_msg': getattr(rsp, 'message', 'Unknown Error')}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_voice(text, save_dir, url_prefix, config):
        if not DASHSCOPE_AVAILABLE: return {'success': False, 'error_msg': "DashScope SDK not installed"}
        api_key = config.get('api_key')
        model = config.get('model_name') or 'qwen3-tts-flash'
        
        base_url = config.get('base_url', '')
        if base_url:
            dashscope.base_http_api_url = base_url

        try:
            rsp = SpeechSynthesizer.call(model=model, api_key=api_key, text=text, format='mp3')
            if rsp.status_code == HTTPStatus.OK:
                if hasattr(rsp, 'get_audio_data'):
                    audio_data = rsp.get_audio_data()
                    if audio_data:
                        fname = f"{uuid.uuid4()}.mp3"
                        save_path = os.path.join(save_dir, fname)
                        with open(save_path, 'wb') as f: f.write(audio_data)
                        return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                return {'success': False, 'error_msg': "No audio data in response"}
            return {'success': False, 'error_msg': getattr(rsp, 'message', 'Unknown Error')}
        except Exception as e:
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
        try:
            resp = requests.post(url, json=payload, headers=OpenAICompatibleHandler._get_headers(config), timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return {'success': True, 'content': data['choices'][0]['message']['content']}
            return {'success': False, 'error_msg': resp.text}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        base_url = config.get('base_url', 'https://api.siliconflow.cn/v1')
        url = f"{base_url.rstrip('/')}/images/generations"
        payload = {
            "model": config.get('model_name', 'black-forest-labs/FLUX.1-schnell'),
            "prompt": prompt,
            "image_size": "1024x1024",
            "batch_size": 1
        }
        try:
            resp = requests.post(url, json=payload, headers=OpenAICompatibleHandler._get_headers(config), timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data'):
                    img_url = data['data'][0]['url']
                    fname = f"{uuid.uuid4()}.png"
                    save_path = os.path.join(save_dir, fname)
                    if download_file(img_url, save_path):
                        return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
            return {'success': False, 'error_msg': resp.text}
        except Exception as e:
            return {'success': False, 'error_msg': str(e)}

class ComfyUIHandler:
    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        return {'success': False, 'error_msg': "ComfyUI generation not implemented yet"}

class MockHandler:
    @staticmethod
    def generate_text(messages, config): return {'success': True, 'content': "Mock Text Response"}
    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        time.sleep(1)
        return {'success': True, 'url': "https://placehold.co/600x400/2c3e50/ffffff?text=Mock+Image"}
    @staticmethod
    def generate_video(prompt, save_dir, url_prefix, config, start_img=None, end_img=None):
        time.sleep(2)
        return {'success': True, 'url': "https://www.w3schools.com/html/mov_bbb.mp4"}
    @staticmethod
    def generate_voice(text, save_dir, url_prefix, config):
        return {'success': True, 'url': "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"}

# ============================================================
#  Dispatcher
# ============================================================

def get_handler(provider_type):
    if provider_type == 'aliyun': return AliyunHandler
    if provider_type == 'siliconflow' or provider_type == 'runninghub': return OpenAICompatibleHandler
    if provider_type == 'comfyui': return ComfyUIHandler
    return MockHandler

# ============================================================
#  Business Logic (Prompt Engineering & Coordination)
# ============================================================

def run_text_generation(messages, config):
    handler = get_handler(config.get('type'))
    return handler.generate_text(messages, config)

def run_script_analysis(script_content, config):
    system_prompt = """
    作为专业的电影分镜师，请分析以下剧本片段，将其转化为分镜表数据。
    **输出要求**：1. 返回一个纯 JSON 数组。2. **必须使用中文**填写所有描述性字段。3. 不要包含 Markdown 标记。
    **JSON对象结构**：- scene: 场次 - shot_number: 镜号 - visual_description: 画面说明 - audio_description: 声音说明 - dialogue: 台词 - duration: 时长 - special_technique: 特殊技术
    """
    messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': f"剧本片段：\n{script_content}"}]
    return run_text_generation(messages, config)

def run_image_generation(visual_desc, style_desc, consistency_text, frame_type, config, save_dir, url_prefix, start_prompt_ref=None, prev_shot_context=""):
    """
    图片生成流程：包含 Prompt 优化逻辑 (Prompt Chaining)
    """
    # 1. 准备 Prompt Engineering 的输入
    consistency_instruction = f"**GLOBAL VISUAL RULES**: {consistency_text}. Maintain consistent characters and environment.\n" if consistency_text else ""
    context_instruction = f"\n**PREVIOUS SHOT CONTEXT**: \"{prev_shot_context}\". Ensure narrative continuity." if prev_shot_context else ""

    sys_prompt = ""
    user_prompt = ""

    if frame_type == 'start':
        sys_prompt = f"""You are an expert AI Art Prompt Engineer. Convert user's description into a high-quality English prompt. {consistency_instruction}{context_instruction} Requirements: 1. Describe subject, environment, lighting, composition, style. 2. Use English, comma-separated. 3. Emphasize cinematic quality. 4. DIRECTLY output prompt text only."""
        user_prompt = f"Style: {style_desc}\nDescription: {visual_desc}"
    else:
        sys_prompt = f"""You are an expert AI Art Prompt Engineer. Generate an [End Frame] prompt based on the [Start Frame Prompt]. {consistency_instruction} Requirements: 1. **KEEP** character appearance, background, and style from Start Frame Prompt EXACTLY the same. 2. **ONLY CHANGE** action/pose based on 'End Frame Description'. 3. Use English. 4. DIRECTLY output prompt text only."""
        user_prompt = f"Start Frame Prompt: {start_prompt_ref}\n\nEnd Frame Action: {visual_desc}"

    # 默认的简单 Prompt (降级策略)
    optimized_prompt = f"{style_desc}, {visual_desc}" 
    if consistency_text: optimized_prompt += f", {consistency_text}"

    # 2. 尝试使用文本模型优化 Prompt
    handler = get_handler(config.get('type', 'mock'))
    
    # 检查 handler 是否支持文本生成，并且当前配置是否有效
    if hasattr(handler, 'generate_text'):
        try:
            # 创建一个用于文本生成的临时配置
            # 主要是为了处理模型名称的问题：用户在生图配置里选的是生图模型 (如 qwen-image-plus)，
            # 我们需要换成一个文本模型 (如 qwen-plus) 来生成 Prompt。
            text_config = config.copy()
            if config.get('type') == 'aliyun':
                text_config['model_name'] = 'qwen-plus'
            elif config.get('type') in ['siliconflow', 'runninghub']:
                # 如果用户没指定文本模型，尝试用通用模型
                text_config['model_name'] = 'Qwen/Qwen2.5-7B-Instruct'
            
            # 执行 Prompt 优化
            res = handler.generate_text([{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}], text_config)
            
            if res['success']:
                optimized_prompt = res['content']
                logger.info(f"[Prompt Eng] Optimized Prompt: {optimized_prompt[:50]}...")
            else:
                logger.warning(f"[Prompt Eng] Failed, using raw prompt. Reason: {res.get('error_msg')}")
        except Exception as e:
            logger.error(f"[Prompt Eng] Exception during optimization: {e}")
            # 保持 optimized_prompt 为默认值

    # 3. 调用生图 API
    # 这里使用原始配置（包含生图模型名称）
    result = handler.generate_image(optimized_prompt, save_dir, url_prefix, config)
    
    return result, optimized_prompt

def run_video_generation(prompt, start_img_path, end_img_path, config, save_dir, url_prefix):
    handler = get_handler(config.get('type'))
    return handler.generate_video(prompt, save_dir, url_prefix, config, start_img=start_img_path, end_img=end_img_path)

def run_voice_generation(text, config, save_dir, url_prefix):
    handler = get_handler(config.get('type'))
    return handler.generate_voice(text, save_dir, url_prefix, config)