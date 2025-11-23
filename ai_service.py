import os
import requests
import time
import json
import base64
import mimetypes
import logging
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath, Path
from typing import Dict, Any, Optional

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
    from dashscope import ImageSynthesis, VideoSynthesis, MultiModalConversation
    logger.info("DashScope SDK imported successfully.")
except ImportError:
    dashscope = None
    logger.warning("Warning: 'dashscope' library not found. AI features will fail.")

def file_to_base64(file_path: str) -> Optional[str]:
    """
    将本地文件转换为 Base64 Data URI 格式
    例如: data:image/png;base64,xxxxxx
    """
    logger.debug(f"[Base64] Converting file: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"[Base64] File not found: {file_path}")
        return None

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'image/png' # 默认类型
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

def generate_aliyun_image(
    prompt: str,
    save_dir: str,
    url_prefix: str,
    api_key: Optional[str] = None,
    model: str = "qwen-image-plus", # 默认模型，也支持 qwen-image
    endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    调用阿里云通义万相/Qwen-VL API 生成图片并保存到本地
    """
    logger.info(f"[Image Gen] Request received. Model: {model}")

    if not dashscope:
        msg = '服务器缺少 dashscope 依赖库'
        logger.error(msg)
        return {'success': False, 'error_msg': msg, 'status_code': 500}

    # 优先使用传入的 Key，否则使用环境变量
    final_api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
    if not final_api_key:
        msg = '未配置 DASHSCOPE_API_KEY'
        logger.error(msg)
        return {'success': False, 'error_msg': msg, 'status_code': 401}

    if endpoint and endpoint.strip():
        dashscope.base_http_api_url = endpoint
        logger.info(f'[Image Gen] Using Custom Endpoint: {endpoint}')
    else:
        # Reset or ignore
        pass

    Path(save_dir).mkdir(parents=True, exist_ok=True)

    # 构造 messages 格式
    messages = [
        {
            "role": "user",
            "content": [
                {"text": prompt}
            ]
        }
    ]

    try:
        logger.info(f'[Image Gen] Calling API... Prompt: {prompt[:50]}...')

        rsp = MultiModalConversation.call(
            api_key=final_api_key,
            model=model,
            messages=messages,
            result_format='message',
            stream=False,
            watermark=False,
            prompt_extend=True,
        )

        logger.info(f"[Image Gen] API Response Status: {rsp.status_code}")

        if rsp.status_code == HTTPStatus.OK:
            img_url = None
            try:
                # 记录完整响应以便调试结构问题
                logger.debug(f"[Image Gen] Full Response: {rsp}")

                content_list = rsp.output.choices[0].message.content
                for item in content_list:
                    if 'image' in item:
                        img_url = item['image']
                        break
            except (AttributeError, IndexError, KeyError, TypeError) as e:
                logger.error(f"[Image Gen] Failed to parse response structure: {e}", exc_info=True)
                return {'success': False, 'error_msg': '无法从响应中解析图片URL', 'status_code': 500}

            if not img_url:
                logger.error("[Image Gen] 'image' field not found in API response content")
                return {'success': False, 'error_msg': 'API响应中未包含图片URL', 'status_code': 500}

            logger.info(f"[Image Gen] Got Image URL: {img_url}")

            # 解析文件名
            file_name = PurePosixPath(unquote(urlparse(img_url).path)).parts[-1]
            if not file_name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                file_name += ".png"

            save_path = Path(save_dir) / file_name

            logger.info(f"[Image Gen] Downloading to: {save_path}")
            image_content = requests.get(img_url, timeout=60).content
            with open(save_path, 'wb+') as f:
                f.write(image_content)

            web_url = f"{url_prefix.rstrip('/')}/{file_name}"

            logger.info(f'[Image Gen] Success. Web URL: {web_url}')
            return {'success': True, 'url': web_url}
        else:
            err_msg = f'Aliyun API Error (Code: {rsp.code}): {rsp.message}'
            logger.error(f"[Image Gen] API Failed: {err_msg}")
            return {
                'success': False,
                'error_msg': err_msg,
                'status_code': rsp.status_code
            }

    except Exception as e:
        logger.exception(f'[Image Gen] Unexpected Exception: {e}')
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
    """
    同步调用阿里云视频生成 API (VideoSynthesis.call)
    支持首尾帧 (通过 Base64 传递)
    """
    logger.info(f"[Video Gen] Request received (Sync). Model: {model}")

    if not dashscope:
        msg = '服务器缺少 dashscope 依赖库'
        logger.error(msg)
        return {'success': False, 'error_msg': msg, 'status_code': 500}

    final_api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
    if not final_api_key:
        msg = '未配置 DASHSCOPE_API_KEY'
        logger.error(msg)
        return {'success': False, 'error_msg': msg, 'status_code': 401}

    if endpoint and endpoint.strip():
        dashscope.base_http_api_url = endpoint
        logger.info(f'[Video Gen] Using Custom Endpoint: {endpoint}')

    # 确保保存目录存在
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f'[Video Gen] Preparing parameters. Prompt: {prompt[:50]}...')

        # 构造参数
        input_params = {
            'model': model,
            'prompt': prompt,
            'prompt_extend': True,
            'resolution': "480P" # 可选
        }

        # 处理本地文件路径：转换为 Base64 Data URI
        if start_img_path:
            logger.info(f"[Video Gen] Processing Start Frame: {start_img_path}")
            base64_start = file_to_base64(start_img_path)
            if base64_start:
                input_params['first_frame_url'] = base64_start
            else:
                logger.error(f"[Video Gen] Failed to convert Start Frame: {start_img_path}")

        if end_img_path:
            logger.info(f"[Video Gen] Processing End Frame: {end_img_path}")
            base64_end = file_to_base64(end_img_path)
            if base64_end:
                input_params['last_frame_url'] = base64_end
            else:
                logger.error(f"[Video Gen] Failed to convert End Frame: {end_img_path}")

        # 同步调用 (Block until done)
        logger.info(f"[Video Gen] Calling VideoSynthesis.call (Sync)... Please wait.")
        rsp = VideoSynthesis.call(api_key=final_api_key, **input_params)

        logger.info(f"[Video Gen] API Response Status: {rsp.status_code}")

        if rsp.status_code == HTTPStatus.OK:
            # 成功，获取 output.video_url
            video_url = rsp.output.video_url
            logger.info(f"[Video Gen] Success! Video URL: {video_url}")

            # 下载视频
            task_id = rsp.output.task_id # 获取 task_id 作为文件名
            file_name = f"{task_id}.mp4"
            save_path = Path(save_dir) / file_name

            logger.info(f'[Video Gen] Downloading video to {save_path}...')
            try:
                video_content = requests.get(video_url, timeout=300).content
                with open(save_path, 'wb+') as f:
                    f.write(video_content)
                logger.info(f"[Video Gen] Download complete.")
            except Exception as dl_err:
                logger.error(f"[Video Gen] Download failed: {dl_err}")
                # 即使下载失败，返回 API 的 URL 作为备用
                return {'success': False, 'status': 'ERROR', 'error_msg': f"Download failed: {dl_err}"}

            web_url = f"{url_prefix.rstrip('/')}/{file_name}"
            return {'success': True, 'url': web_url}

        else:
            err_msg = f'Generation Failed: Code={rsp.code}, Msg={rsp.message}'
            logger.error(f"[Video Gen] {err_msg}")
            return {
                'success': False,
                'error_msg': err_msg,
                'status_code': rsp.status_code
            }

    except Exception as e:
        logger.exception(f'[Video Gen] Exception: {e}')
        return {'success': False, 'error_msg': str(e), 'status_code': 500}
