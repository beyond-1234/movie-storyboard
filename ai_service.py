import os
import time
import json
import base64
import mimetypes
import logging
import requests
import uuid
import random
import hmac
import hashlib
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath, Path
from typing import Dict, Any, Optional, List
from zai import ZhipuAiClient

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

class ViduHandler:
    """
    VIDU API Handler - Start-End to Video
    官方文档: https://api.vidu.com/ent/v2/start-end2video
    支持首尾帧生成视频
    """
    
    @staticmethod
    def _get_headers(config):
        return {
            "Authorization": f"Token {config.get('api_key')}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def _wait_for_video(task_id, config, max_wait=600):
        """
        轮询等待视频生成完成
        max_wait: 最大等待时间(秒)，默认10分钟（off_peak模式可能需要48小时）
        """
        import time
        base_url = config.get('base_url', 'https://api.vidu.com')
        url = f"{base_url.rstrip('/')}/ent/v2/tasks/{task_id}/creations" 
        headers = ViduHandler._get_headers(config)
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    state = data.get('state')
                    err_code = data.get('err_code')
                    
                    logger.info(f"[VIDU] Task {task_id} state: {state} err_code: {err_code}")
                    
                    if state == 'success':
                        # 成功，获取视频URL
                        video_url = data.get('video_url') or data.get('video')
                        if video_url:
                            return {'success': True, 'url': video_url, 'data': data}
                        else:
                            return {'success': False, 'error_msg': 'No video URL in response'}
                    
                    elif state == 'failed':
                        error_msg = data.get('error', 'Generation failed')
                        return {'success': False, 'error_msg': error_msg}
                    
                    elif state in ['created', 'queueing', 'processing']:
                        # 继续等待
                        time.sleep(10)  # 每10秒查询一次
                    
                    else:
                        logger.warning(f"[VIDU] Unknown state: {state}")
                        time.sleep(10)
                else:
                    logger.error(f"[VIDU] Query failed: {resp.status_code} - {resp.text}")
                    if resp.status_code == 404:
                        return {'success': False, 'error_msg': 'Task not found'}
                    time.sleep(10)
                    
            except Exception as e:
                logger.error(f"[VIDU] Query error: {e}")
                time.sleep(10)
        
        return {'success': False, 'error_msg': f'Timeout after {max_wait}s waiting for video generation'}
    
    @staticmethod
    def generate_video(prompt, save_dir, url_prefix, config, start_img=None, end_img=None):
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
        
        # 转换图片为 base64
        start_img_b64 = file_to_base64(start_img)
        end_img_b64 = file_to_base64(end_img)
        
        if not start_img_b64 or not end_img_b64:
            return {'success': False, 'error_msg': "Failed to encode images to base64"}
        
        # API endpoint
        url = f"{base_url.rstrip('/')}/ent/v2/start-end2video"
        
        # 构建请求参数
        payload = {
            "model": model,
            "images": [start_img_b64, end_img_b64],  # 首帧和尾帧
            "prompt": "",
            "duration": 2,  # 默认5秒，可根据模型调整
            "resolution": "360p",  # 默认720p，可选: 540p, 720p, 1080p
            "movement_amplitude": "auto",  # auto, small, medium, large
            "off_peak": False,  # 非高峰模式
            "bgm": False  # 不添加背景音乐
        }
        
        # 可选：如果需要固定随机种子
        # payload["seed"] = 42
        
        try:
            headers = ViduHandler._get_headers(config)
            logger.info(f"[VIDU] Creating task with model: {model}")
            
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                task_id = data.get('task_id')
                state = data.get('state')
                credits = data.get('credits', 0)
                
                logger.info(f"[VIDU] Task created: {task_id}, state: {state}, credits: {credits}")
                
                if not task_id:
                    return {'success': False, 'error_msg': 'No task_id returned from API'}
                
                # 等待视频生成完成
                result = ViduHandler._wait_for_video(task_id, config, max_wait=600)
                
                if result['success'] and result.get('url'):
                    video_url = result['url']
                    
                    # 下载视频到本地
                    fname = f"{task_id}.mp4"
                    save_path = os.path.join(save_dir, fname)
                    
                    logger.info(f"[VIDU] Downloading video from: {video_url}")
                    
                    if download_file(video_url, save_path):
                        logger.info(f"[VIDU] Video saved to: {save_path}")
                        return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                    else:
                        # 下载失败，返回远程URL
                        logger.warning(f"[VIDU] Download failed, returning remote URL")
                        return {'success': True, 'url': video_url}
                
                return result
            
            else:
                # API调用失败
                error_msg = resp.text
                try:
                    error_data = resp.json()
                    error_msg = error_data.get('error', {}).get('message', error_msg)
                except:
                    pass
                
                logger.error(f"[VIDU] API Error {resp.status_code}: {error_msg}")
                return {'success': False, 'error_msg': f"API Error ({resp.status_code}): {error_msg}"}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error_msg': 'Request timeout'}
        except Exception as e:
            logger.exception("[VIDU] Generation failed")
            return {'success': False, 'error_msg': str(e)}
    
    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        """
        VIDU 不支持图片生成，返回错误
        """
        return {'success': False, 'error_msg': "VIDU only supports video generation (start-end to video)"}
    
    @staticmethod
    def generate_text(messages, config):
        """
        VIDU 不支持文本生成，返回错误
        """
        return {'success': False, 'error_msg': "VIDU does not support text generation"}

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
    def _sign_request(access_key, secret_key, req_body):
        """
        火山引擎 V4 签名
        返回 (headers, request_url)
        """
        from datetime import datetime
        
        if not access_key or not secret_key:
            raise ValueError('Missing access_key or secret_key')
        
        # 时间戳
        t = datetime.utcnow()
        current_date = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d')
        
        # 查询参数
        query_params = {
            'Action': 'CVProcess',
            'Version': '2022-08-31',
        }
        canonical_querystring = JimengHandler._format_query(query_params)
        
        # 请求路径
        canonical_uri = '/'
        
        # 计算 payload hash
        payload_hash = hashlib.sha256(req_body.encode('utf-8')).hexdigest()
        
        # 请求头
        content_type = 'application/json'
        signed_headers = 'content-type;host;x-content-sha256;x-date'
        canonical_headers = (
            f'content-type:{content_type}\n'
            f'host:{JimengHandler.HOST}\n'
            f'x-content-sha256:{payload_hash}\n'
            f'x-date:{current_date}\n'
        )
        
        # 构建规范请求
        canonical_request = (
            f'{JimengHandler.METHOD}\n'
            f'{canonical_uri}\n'
            f'{canonical_querystring}\n'
            f'{canonical_headers}\n'
            f'{signed_headers}\n'
            f'{payload_hash}'
        )
        
        # 构建签名字符串
        algorithm = 'HMAC-SHA256'
        credential_scope = f'{datestamp}/{JimengHandler.REGION}/{JimengHandler.SERVICE}/request'
        string_to_sign = (
            f'{algorithm}\n'
            f'{current_date}\n'
            f'{credential_scope}\n'
            f'{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        )
        
        # 计算签名
        signing_key = JimengHandler._get_signature_key(
            secret_key, datestamp, JimengHandler.REGION, JimengHandler.SERVICE
        )
        signature = hmac.new(
            signing_key, 
            string_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        
        # 构建 Authorization 头
        authorization_header = (
            f'{algorithm} '
            f'Credential={access_key}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, '
            f'Signature={signature}'
        )
        
        # 最终请求头
        headers = {
            'X-Date': current_date,
            'Authorization': authorization_header,
            'X-Content-Sha256': payload_hash,
            'Content-Type': content_type
        }
        
        # 请求 URL
        request_url = f'{JimengHandler.ENDPOINT}?{canonical_querystring}'
        
        return headers, request_url
    
    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        """
        即梦文生图 API
        """
        api_key_combined = config.get('api_key')
        model = config.get('model_name', 'high_aes')
        
        try:
            # 解析凭证
            access_key, secret_key = JimengHandler._parse_credentials(api_key_combined)
        except ValueError as e:
            return {'success': False, 'error_msg': str(e)}
        
        # 构建请求体
        body_params = {
            "req_key": model,
            "prompt": prompt,
            "width": 1024,
            "height": 1024,
            "seed": -1,
        }
        req_body = json.dumps(body_params)
        
        try:
            # 签名请求
            headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body)
            
            logger.info(f"[Jimeng] Generating image with model: {model}, prompt: {prompt[:50]}...")
            
            # 发送请求
            resp = requests.post(request_url, headers=headers, data=req_body, timeout=120)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # 检查返回状态
                code = data.get('code')
                if code == 10000:  # 火山引擎成功状态码
                    # 获取图片数据
                    resp_data = data.get('data', {})
                    
                    # 可能返回 binary_data_base64 数组
                    binary_data_list = resp_data.get('binary_data_base64', [])
                    
                    if binary_data_list:
                        # 解析 base64 图片
                        img_base64 = binary_data_list[0]
                        
                        # 如果包含 data:image 前缀
                        if ',' in img_base64:
                            img_base64 = img_base64.split(',', 1)[1]
                        
                        img_bytes = base64.b64decode(img_base64)
                        
                        fname = f"{uuid.uuid4()}.png"
                        save_path = os.path.join(save_dir, fname)
                        
                        with open(save_path, 'wb') as f:
                            f.write(img_bytes)
                        
                        logger.info(f"[Jimeng] Image saved to: {save_path}")
                        return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                    
                    # 也可能直接返回 image_url
                    img_url = resp_data.get('image_url')
                    if img_url:
                        fname = f"{uuid.uuid4()}.png"
                        save_path = os.path.join(save_dir, fname)
                        
                        if download_file(img_url, save_path):
                            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"[Jimeng] API Error code={code}: {error_msg}")
                return {'success': False, 'error_msg': f"API Error (code={code}): {error_msg}"}
            
            else:
                error_msg = resp.text
                logger.error(f"[Jimeng] HTTP Error {resp.status_code}: {error_msg}")
                return {'success': False, 'error_msg': f"HTTP Error ({resp.status_code}): {error_msg}"}
                
        except ValueError as e:
            return {'success': False, 'error_msg': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error_msg': 'Request timeout'}
        except Exception as e:
            logger.exception("[Jimeng] Image generation failed")
            return {'success': False, 'error_msg': str(e)}
    
    @staticmethod
    def generate_video(prompt, save_dir, url_prefix, config, start_img=None, end_img=None):
        """
        即梦首尾帧生视频 API
        需要提供首帧,尾帧可选
        """
        api_key_combined = config.get('api_key')
        model = config.get('model_name', 'i2v_high_aes')
        
        try:
            # 解析凭证
            access_key, secret_key = JimengHandler._parse_credentials(api_key_combined)
        except ValueError as e:
            return {'success': False, 'error_msg': str(e)}
        
        if not start_img:
            return {'success': False, 'error_msg': "Jimeng video generation requires start frame"}
        
        # 转换图片为 base64 (只要 base64 部分,不要 data:image 前缀)
        start_img_b64 = file_to_base64(start_img)
        if start_img_b64 and ',' in start_img_b64:
            start_img_b64 = start_img_b64.split(',', 1)[1]
        
        end_img_b64 = None
        if end_img:
            end_img_b64 = file_to_base64(end_img)
            if end_img_b64 and ',' in end_img_b64:
                end_img_b64 = end_img_b64.split(',', 1)[1]
        
        if not start_img_b64:
            return {'success': False, 'error_msg': "Failed to encode start image to base64"}
        
        # 构建请求体
        body_params = {
            "req_key": model,
            "binary_data_base64": [start_img_b64],
            "prompt": prompt,
            "frames": 121
        }
        
        # 如果有尾帧,添加到数组
        if end_img_b64:
            body_params["binary_data_base64"].append(end_img_b64)
        
        req_body = json.dumps(body_params)
        
        try:
            # 签名请求
            headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body)
            
            logger.info(f"[Jimeng] Creating video task with model: {model}")
            
            # 1. 创建任务
            resp = requests.post(request_url, headers=headers, data=req_body, timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                code = data.get('code')
                
                if code == 10000:  # 成功创建任务
                    resp_data = data.get('data', {})
                    
                    # 检查是否是异步任务
                    if 'task_id' in resp_data:
                        task_id = resp_data['task_id']
                        logger.info(f"[Jimeng] Async task created: {task_id}")
                        
                        # 轮询等待视频生成完成
                        result = JimengHandler._wait_for_video(task_id, access_key, secret_key, max_wait=600)
                        
                        if result['success']:
                            # 处理 base64 视频
                            if result.get('base64'):
                                video_bytes = base64.b64decode(result['base64'])
                                
                                fname = f"{task_id}.mp4"
                                save_path = os.path.join(save_dir, fname)
                                
                                with open(save_path, 'wb') as f:
                                    f.write(video_bytes)
                                
                                logger.info(f"[Jimeng] Video saved to: {save_path}")
                                return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                            
                            # 处理 URL 视频
                            elif result.get('url'):
                                video_url = result['url']
                                fname = f"{task_id}.mp4"
                                save_path = os.path.join(save_dir, fname)
                                
                                logger.info(f"[Jimeng] Downloading video from: {video_url}")
                                
                                if download_file(video_url, save_path):
                                    logger.info(f"[Jimeng] Video saved to: {save_path}")
                                    return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                                else:
                                    logger.warning(f"[Jimeng] Download failed, returning remote URL")
                                    return {'success': True, 'url': video_url}
                        
                        return result
                    
                    # 同步返回视频数据
                    elif 'binary_data_base64' in resp_data:
                        video_base64_list = resp_data.get('binary_data_base64', [])
                        if video_base64_list:
                            video_base64 = video_base64_list[0]
                            if ',' in video_base64:
                                video_base64 = video_base64.split(',', 1)[1]
                            
                            video_bytes = base64.b64decode(video_base64)
                            
                            fname = f"{uuid.uuid4()}.mp4"
                            save_path = os.path.join(save_dir, fname)
                            
                            with open(save_path, 'wb') as f:
                                f.write(video_bytes)
                            
                            logger.info(f"[Jimeng] Video saved to: {save_path}")
                            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"[Jimeng] API Error code={code}: {error_msg}")
                return {'success': False, 'error_msg': f"API Error (code={code}): {error_msg}"}
            
            else:
                error_msg = resp.text
                logger.error(f"[Jimeng] HTTP Error {resp.status_code}: {error_msg}")
                return {'success': False, 'error_msg': f"HTTP Error ({resp.status_code}): {error_msg}"}
                
        except ValueError as e:
            return {'success': False, 'error_msg': str(e)}
        except requests.exceptions.Timeout:
            return {'success': False, 'error_msg': 'Request timeout'}
        except Exception as e:
            logger.exception("[Jimeng] Video generation failed")
            return {'success': False, 'error_msg': str(e)}
    
    @staticmethod
    def _wait_for_video(task_id, access_key, secret_key, max_wait=600):
        """
        轮询等待视频生成完成
        使用火山引擎查询接口
        """
        import time
        from datetime import datetime
        
        # 查询请求体
        body_params = {
            "req_key": "query_async",
            "task_id": task_id
        }
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                req_body = json.dumps(body_params)
                
                # 签名请求
                headers, request_url = JimengHandler._sign_request(access_key, secret_key, req_body)
                
                resp = requests.post(request_url, headers=headers, data=req_body, timeout=30)
                
                if resp.status_code == 200:
                    data = resp.json()
                    code = data.get('code')
                    
                    logger.info(f"[Jimeng] Task {task_id} status code: {code}")
                    
                    if code == 10000:
                        # 任务完成
                        resp_data = data.get('data', {})
                        status = resp_data.get('status')
                        
                        if status == 'done':
                            # 获取视频数据
                            binary_data_list = resp_data.get('binary_data_base64', [])
                            if binary_data_list:
                                # 视频以 base64 返回
                                video_base64 = binary_data_list[0]
                                if ',' in video_base64:
                                    video_base64 = video_base64.split(',', 1)[1]
                                
                                return {'success': True, 'base64': video_base64}
                            
                            # 或者返回 URL
                            video_url = resp_data.get('video_url')
                            if video_url:
                                return {'success': True, 'url': video_url}
                            
                            return {'success': False, 'error_msg': 'No video data in response'}
                        
                        elif status == 'failed':
                            error_msg = resp_data.get('message', 'Generation failed')
                            return {'success': False, 'error_msg': error_msg}
                        
                        elif status in ['processing', 'pending']:
                            # 继续等待
                            logger.info(f"[Jimeng] Task {task_id} still processing...")
                            time.sleep(10)
                        
                        else:
                            logger.warning(f"[Jimeng] Unknown status: {status}")
                            time.sleep(10)
                    
                    elif code == 10001:
                        # 任务处理中
                        time.sleep(10)
                    
                    else:
                        error_msg = data.get('message', 'Query failed')
                        logger.error(f"[Jimeng] Query error code={code}: {error_msg}")
                        time.sleep(10)
                
                else:
                    logger.error(f"[Jimeng] Query HTTP error: {resp.status_code}")
                    time.sleep(10)
                    
            except Exception as e:
                logger.error(f"[Jimeng] Query exception: {e}")
                time.sleep(10)
        
        return {'success': False, 'error_msg': f'Timeout after {max_wait}s waiting for video generation'}
    
    @staticmethod
    def generate_text(messages, config):
        """
        即梦不支持文本生成
        """
        return {'success': False, 'error_msg': "Jimeng does not support text generation"}



class MiniMaxHandler:
    @staticmethod
    def _get_headers(config):
        return {
            "Authorization": f"Bearer {config.get('api_key')}",
            "Content-Type": "application/json"
        }

    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        """
        MiniMax 文生图 API
        官方文档: https://platform.minimaxi.com/docs/api-reference/image/generation/api/text-to-image
        """
        api_key = config.get('api_key')
        model = config.get('model_name', 'image-01')
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        
        if not api_key:
            return {'success': False, 'error_msg': "MiniMax API key is required"}
        
        # 构建请求参数
        payload = {
            "model": model,
            "prompt": prompt,
            "response_format": "url",  # 使用URL格式返回图片
            "n": 1,  # 生成1张图片
        }
        
        # 添加可选参数
        if config.get('aspect_ratio'):
            payload["aspect_ratio"] = config.get('aspect_ratio')
        elif config.get('width') and config.get('height'):
            # 仅当model为image-01时生效
            if model == 'image-01':
                payload["width"] = config.get('width')
                payload["height"] = config.get('height')
        
        # 添加风格参数（仅当model为image-01-live时生效）
        if model == 'image-01-live' and config.get('style_type'):
            payload["style"] = {
                "style_type": config.get('style_type'),
                "style_weight": config.get('style_weight', 0.8)
            }
        
        # 添加其他可选参数
        if config.get('seed') is not None:
            payload["seed"] = config.get('seed')
        if config.get('prompt_optimizer') is not None:
            payload["prompt_optimizer"] = config.get('prompt_optimizer')
        if config.get('aigc_watermark') is not None:
            payload["aigc_watermark"] = config.get('aigc_watermark')
        
        try:
            url = f"{base_url.rstrip('/')}/v1/image_generation"
            headers = MiniMaxHandler._get_headers(config)
            
            logger.info(f"[MiniMax] Generating image with model: {model}, prompt: {prompt[:50]}...")
            
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # 检查API响应
                base_resp = data.get('base_resp', {})
                status_code = base_resp.get('status_code')
                
                if status_code == 0:  # 成功
                    # 获取图片URL
                    image_urls = data.get('data', {}).get('image_urls', [])
                    
                    if image_urls and len(image_urls) > 0:
                        img_url = image_urls[0]
                        
                        # 下载图片到本地
                        fname = f"{uuid.uuid4()}.png"
                        save_path = os.path.join(save_dir, fname)
                        
                        if download_file(img_url, save_path):
                            logger.info(f"[MiniMax] Image saved to: {save_path}")
                            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                        else:
                            # 下载失败，返回远程URL
                            logger.warning(f"[MiniMax] Download failed, returning remote URL")
                            return {'success': True, 'url': img_url}
                    
                    return {'success': False, 'error_msg': "No image URL in response"}
                else:
                    # API返回错误
                    error_msg = base_resp.get('status_msg', 'Unknown error')
                    logger.error(f"[MiniMax] API Error {status_code}: {error_msg}")
                    return {'success': False, 'error_msg': f"API Error ({status_code}): {error_msg}"}
            else:
                # HTTP请求失败
                error_msg = resp.text
                logger.error(f"[MiniMax] HTTP Error {resp.status_code}: {error_msg}")
                return {'success': False, 'error_msg': f"HTTP Error ({resp.status_code}): {error_msg}"}
        
        except requests.exceptions.Timeout:
            return {'success': False, 'error_msg': 'Request timeout'}
        except Exception as e:
            logger.exception("[MiniMax] Image generation failed")
            return {'success': False, 'error_msg': str(e)}
    
    @staticmethod
    def generate_text(messages, config):
        """
        MiniMax 不支持文本生成，返回错误
        """
        return {'success': False, 'error_msg': "MiniMax does not support text generation"}
    
    @staticmethod
    def generate_video(prompt, save_dir, url_prefix, config, start_img=None, end_img=None):
        """
        MiniMax 首尾帧生成视频 API
        官方文档: https://platform.minimaxi.com/docs/api-reference/video/generation/api/start-end-to-video
        """
        api_key = config.get('api_key')
        model = config.get('model_name', 'MiniMax-Hailuo-02')
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        
        if not api_key:
            return {'success': False, 'error_msg': "MiniMax API key is required"}
        
        if not start_img or not end_img:
            return {'success': False, 'error_msg': "MiniMax video generation requires both start and end frame images"}
        
        # 转换图片为 base64
        start_img_b64 = file_to_base64(start_img)
        end_img_b64 = file_to_base64(end_img)
        
        if not start_img_b64 or not end_img_b64:
            return {'success': False, 'error_msg': "Failed to encode images to base64"}
        
        # 构建请求参数
        payload = {
            "model": model,
            "first_frame_image": start_img_b64,
            "last_frame_image": end_img_b64,
            "prompt": prompt,
            "prompt_optimizer": config.get('prompt_optimizer', True),
            "duration": config.get('duration', 6),
            "resolution": config.get('resolution', '768P')
        }
        
        # 添加可选参数
        if config.get('callback_url'):
            payload["callback_url"] = config.get('callback_url')
        if config.get('aigc_watermark') is not None:
            payload["aigc_watermark"] = config.get('aigc_watermark')
        
        try:
            url = f"{base_url.rstrip('/')}/v1/video_generation"
            headers = MiniMaxHandler._get_headers(config)
            
            logger.info(f"[MiniMax] Creating video task with model: {model}, prompt: {prompt[:50]}...")
            
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # 检查API响应
                base_resp = data.get('base_resp', {})
                status_code = base_resp.get('status_code')
                
                if status_code == 0:  # 成功
                    task_id = data.get('task_id')
                    
                    if not task_id:
                        return {'success': False, 'error_msg': "No task_id returned from API"}
                    
                    logger.info(f"[MiniMax] Video task created: {task_id}")
                    
                    # 轮询等待视频生成完成
                    result = MiniMaxHandler._wait_for_video(task_id, config, max_wait=600)
                    
                    if result['success'] and result.get('url'):
                        video_url = result['url']
                        
                        # 下载视频到本地
                        fname = f"{task_id}.mp4"
                        save_path = os.path.join(save_dir, fname)
                        
                        logger.info(f"[MiniMax] Downloading video from: {video_url}")
                        
                        if download_file(video_url, save_path):
                            logger.info(f"[MiniMax] Video saved to: {save_path}")
                            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                        else:
                            # 下载失败，返回远程URL
                            logger.warning(f"[MiniMax] Download failed, returning remote URL")
                            return {'success': True, 'url': video_url}
                    
                    return result
                else:
                    # API返回错误
                    error_msg = base_resp.get('status_msg', 'Unknown error')
                    logger.error(f"[MiniMax] API Error {status_code}: {error_msg}")
                    return {'success': False, 'error_msg': f"API Error ({status_code}): {error_msg}"}
            else:
                # HTTP请求失败
                error_msg = resp.text
                logger.error(f"[MiniMax] HTTP Error {resp.status_code}: {error_msg}")
                return {'success': False, 'error_msg': f"HTTP Error ({resp.status_code}): {error_msg}"}
        
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
        import time
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        url = f"{base_url.rstrip('/')}/v1/query/video_generation?task_id={task_id}"
        headers = MiniMaxHandler._get_headers(config)
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    base_resp = data.get('base_resp', {})
                    status_code = base_resp.get('status_code')
                    
                    if status_code == 0:
                        status = data.get('status')
                        file_id = data.get('file_id')
                        
                        logger.info(f"[MiniMax] Task {task_id} status: {status}")
                        
                        if status == 'Success':
                            # 成功，获取视频URL
                            video_url = data.get('video_url')
                            if video_url:
                                return {'success': True, 'url': video_url, 'data': data}
                            else:
                                return {'success': False, 'error_msg': 'No video URL in response'}
                        
                        elif status == 'Failed':
                            error_msg = data.get('error_message', 'Generation failed')
                            return {'success': False, 'error_msg': error_msg}
                        
                        elif status in ['Processing', 'Queueing']:
                            # 继续等待
                            time.sleep(10)  # 每10秒查询一次
                        
                        else:
                            logger.warning(f"[MiniMax] Unknown status: {status}")
                            time.sleep(10)
                    else:
                        logger.error(f"[MiniMax] Query failed: {status_code} - {base_resp.get('status_msg')}")
                        time.sleep(10)
                else:
                    logger.error(f"[MiniMax] Query HTTP error: {resp.status_code}")
                    time.sleep(10)
            
            except Exception as e:
                logger.error(f"[MiniMax] Query error: {e}")
                time.sleep(10)
        
        return {'success': False, 'error_msg': f'Timeout after {max_wait}s waiting for video generation'}

    @staticmethod
    def fuse_image(prompt, save_dir, url_prefix, config, base_image_path, ref_image_path_list):

        """
        MiniMax 图生图 API
        官方文档: https://platform.minimaxi.com/docs/api-reference/image/generation/api/image-to-image
        当前只支持角色图生图
        """
        api_key = config.get('api_key')
        model = config.get('model_name', 'image-01')
        base_url = config.get('base_url', 'https://api.minimaxi.com')
        
        if not api_key:
            return {'success': False, 'error_msg': "MiniMax API key is required"}
        
        # 海螺AI支持支角色图生图
        ref_image_path_list.append(base_image_path)
        
        # 转换参考图为 base64
        subject_references = []
        for image_path in ref_image_path_list:
            image_b64 = file_to_base64(image_path)
            if not image_b64:
                return {'success': False, 'error_msg': f"Failed to encode reference image {image_path} to base64"}
            
            subject_references.append({
                "type": "character",
                "image_file": image_b64
            })
        
        # 构建请求参数
        payload = {
            "model": model,
            "prompt": prompt,
            "subject_reference": subject_references,
            "response_format": "url",
            "n": 1
        }
        
        # 添加可选参数
        if config.get('aspect_ratio'):
            payload["aspect_ratio"] = config.get('aspect_ratio')
        elif config.get('width') and config.get('height'):
            if model == 'image-01':
                payload["width"] = config.get('width')
                payload["height"] = config.get('height')
        
        if model == 'image-01-live' and config.get('style_type'):
            payload["style"] = {
                "style_type": config.get('style_type'),
                "style_weight": config.get('style_weight', 0.8)
            }
        
        if config.get('seed') is not None:
            payload["seed"] = config.get('seed')
        if config.get('prompt_optimizer') is not None:
            payload["prompt_optimizer"] = config.get('prompt_optimizer')
        if config.get('aigc_watermark') is not None:
            payload["aigc_watermark"] = config.get('aigc_watermark')
        
        try:
            url = f"{base_url.rstrip('/')}/v1/image_generation"
            headers = MiniMaxHandler._get_headers(config)
            
            logger.info(f"[MiniMax] Generating image from image with model: {model}, prompt: {prompt[:50]}...")
            
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            
            if resp.status_code == 200:
                data = resp.json()
                base_resp = data.get('base_resp', {})
                status_code = base_resp.get('status_code')
                
                if status_code == 0:
                    image_urls = data.get('data', {}).get('image_urls', [])
                    
                    if image_urls and len(image_urls) > 0:
                        img_url = image_urls[0]
                        fname = f"{uuid.uuid4()}.png"
                        save_path = os.path.join(save_dir, fname)
                        
                        if download_file(img_url, save_path):
                            logger.info(f"[MiniMax] Image saved to: {save_path}")
                            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                        else:
                            logger.warning(f"[MiniMax] Download failed, returning remote URL")
                            return {'success': True, 'url': img_url}
                    
                    return {'success': False, 'error_msg': "No image URL in response"}
                else:
                    error_msg = base_resp.get('status_msg', 'Unknown error')
                    logger.error(f"[MiniMax] API Error {status_code}: {error_msg}")
                    return {'success': False, 'error_msg': f"API Error ({status_code}): {error_msg}"}
            else:
                error_msg = resp.text
                logger.error(f"[MiniMax] HTTP Error {resp.status_code}: {error_msg}")
                return {'success': False, 'error_msg': f"HTTP Error ({resp.status_code}): {error_msg}"}
        
        except requests.exceptions.Timeout:
            return {'success': False, 'error_msg': 'Request timeout'}
        except Exception as e:
            logger.exception("[MiniMax] Image generation from image failed")
            return {'success': False, 'error_msg': str(e)}


class ZhipuHandler:
    @staticmethod
    def generate_text(messages, config):
        try:
            api_key = config.get('api_key')
            if not api_key:
                return {'success': False, 'error_msg': "Zhipu API key is required"}
            
            model = config.get('model_name') or 'glm-4.6'
            client = ZhipuAiClient(api_key=api_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            
            if response.choices:
                return {'success': True, 'content': response.choices[0].message.content}
            return {'success': False, 'error_msg': "No response from Zhipu API"}
            
        except Exception as e:
            logger.error(f"[Zhipu] Text generation error: {e}")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_image(prompt, save_dir, url_prefix, config):
        try:
            api_key = config.get('api_key')
            if not api_key:
                return {'success': False, 'error_msg': "Zhipu API key is required"}
            
            model = config.get('model_name') or 'cogview-3'
            client = ZhipuAiClient(api_key=api_key)
            
            response = client.images.generations(
                model=model,
                prompt=prompt,
                size=config.get('size', "1024x1024"),
                quality=config.get('quality', "standard")
            )
            
            if response.data and len(response.data) > 0:
                img_url = response.data[0].url
                fname = f"{uuid.uuid4()}.png"
                save_path = os.path.join(save_dir, fname)
                
                if download_file(img_url, save_path):
                    return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                return {'success': False, 'error_msg': "Failed to download image"}
            
            return {'success': False, 'error_msg': "No image data in response"}
            
        except Exception as e:
            logger.error(f"[Zhipu] Image generation error: {e}")
            return {'success': False, 'error_msg': str(e)}

    @staticmethod
    def generate_video(prompt, save_dir, url_prefix, config, start_img=None, end_img=None):
        try:
            api_key = config.get('api_key')
            if not api_key:
                return {'success': False, 'error_msg': "Zhipu API key is required"}
            
            if not start_img:
                return {'success': False, 'error_msg': "Zhipu video generation requires start image"}
            
            # 处理起始图片为base64
            start_img_b64 = file_to_base64(start_img)
            end_img_b64 = file_to_base64(end_img)
            if not start_img_b64 or not end_img_b64:
                return {'success': False, 'error_msg': "Failed to encode start image to base64"}
            
            model = config.get('model_name') or 'cogvideox-2'
            client = ZhipuAiClient(api_key=api_key)
            
            # 提交视频生成任务
            response = client.videos.generations(
                model=model,
                image_url=[start_img_b64, end_img_b64],
                prompt=prompt,
                quality=config.get('quality', "speed"),
                with_audio=config.get('with_audio', True),
                size=config.get('size', "1280x720"),
                fps=config.get('fps', 30)
            )
            
            if not response.id:
                return {'success': False, 'error_msg': "No task ID returned from API"}
            
            # 轮询等待结果
            max_wait = config.get('max_wait', 600)
            start_time = time.time()
            while time.time() - start_time < max_wait:
                result = client.videos.retrieve_videos_result(id=response.id)
                
                if result.status == 'succeeded':
                    video_url = result.data[0].url if result.data else None
                    if video_url:
                        fname = f"{response.id}.mp4"
                        save_path = os.path.join(save_dir, fname)
                        
                        if download_file(video_url, save_path):
                            return {'success': True, 'url': f"{url_prefix.rstrip('/')}/{fname}"}
                        return {'success': True, 'url': video_url}
                    return {'success': False, 'error_msg': "No video URL in response"}
                
                if result.status == 'failed':
                    return {'success': False, 'error_msg': f"Video generation failed: {result.failure_details}"}
                
                time.sleep(10)  # 每10秒查询一次
            
            return {'success': False, 'error_msg': f"Timeout after {max_wait}s waiting for video"}
            
        except Exception as e:
            logger.error(f"[Zhipu] Video generation error: {e}")
            return {'success': False, 'error_msg': str(e)}

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
    handler = get_handler(config.get('type'))
    return handler.generate_text(messages, config)


def run_image_generation(visual_desc, style_desc, consistency_text, frame_type, config, save_dir, url_prefix, start_prompt_ref=None, prev_shot_context=""):
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
    
    # 默认的简单 Prompt (降级策略)
    optimized_prompt = f"{style_desc}, {visual_desc}" 
    if consistency_text: optimized_prompt += f", {consistency_text}"

    # 2. 尝试使用文本模型优化 Prompt
    handler = get_handler('aliyun')
    
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
            elif config.get('type') == 'zai':
                text_config['model_name'] = 'glm-4.6'
            
            # 执行 Prompt 优化
            logger.info("start prompt eng")
            res = handler.generate_text([{'role': 'system', 'content': sys_prompt + " 使用中文回答"}, {'role': 'user', 'content': user_prompt}], text_config)
            
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
    handler = get_handler(config.get('type'))
    return handler.generate_video(prompt, save_dir, url_prefix, config, start_img=start_img_path, end_img=end_img_path)

def run_simple_image_generation(prompt, config, save_dir, url_prefix):
    """
    不带提示词工程的简单图片生成方法
    直接使用用户提供的prompt，不进行任何优化
    """
    logger.info(f"[Simple Image Gen] Starting generation with prompt: {prompt[:50]}...")
    
    handler = get_handler(config.get('type', 'mock'))
    result = handler.generate_image(prompt, save_dir, url_prefix, config)
    
    if result.get('success'):
        logger.info(f"[Simple Image Gen] Generation successful. URL: {result.get('url', 'N/A')}")
    else:
        logger.error(f"[Simple Image Gen] Generation failed. Error: {result.get('error_msg', 'Unknown error')}")
    
    return result

def run_voice_generation(text, config, save_dir, url_prefix):
    handler = get_handler(config.get('type'))
    return handler.generate_voice(text, save_dir, url_prefix, config)

def run_fusion_generation(base_image_path, fusion_prompt, config, save_dir, url_prefix, element_image_paths):
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
    logger.info(f"[Fusion Gen] Starting fusion. Base: {base_image_path}, Prompt: {fusion_prompt[:30]}...")
    handler = get_handler(config.get('type', 'mock'))
    
    # 传入 ref_image_path 参数，Handler 内部会判断是否调用图生图接口
    result = handler.fuse_image(fusion_prompt, save_dir, url_prefix, config, base_image_path, element_image_paths=element_image_paths)
    return result