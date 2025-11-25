import os
import json
import shutil
import uuid
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JianyingExporter")

JIANYING_AVAILABLE = False
try:
    import pyJianYingDraft as draft
    from pyJianYingDraft import trange
    JIANYING_AVAILABLE = True
except ImportError:
    logger.warning("pyJianYingDraft library not found. Export features will be disabled.")

def parse_duration(duration_str):
    """解析时长字符串，如 '3s', '3.5'，返回浮点数秒。默认 3.0s"""
    if not duration_str: return 3.0
    try:
        clean = str(duration_str).lower().replace('s', '').strip()
        val = float(clean)
        return val if val > 0 else 3.0
    except:
        return 3.0

def copy_asset(source_path, dest_folder, prefix=""):
    """
    复制资源文件到目标目录，并返回新的绝对路径
    """
    if not source_path:
        return None
        
    # 处理相对路径转绝对路径
    if not os.path.isabs(source_path):
        # 假设是相对于当前工作目录
        source_path = os.path.abspath(source_path)

    if not os.path.exists(source_path):
        logger.warning(f"Source file not found: {source_path}")
        return None
    
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder, exist_ok=True)
        
    filename = os.path.basename(source_path)
    # 简单的文件名清洗，防止特殊字符报错
    clean_filename = "".join([c for c in filename if c.isalnum() or c in '._-'])
    if prefix:
        new_filename = f"{prefix}_{clean_filename}"
    else:
        new_filename = clean_filename
        
    dest_path = os.path.join(dest_folder, new_filename)
    
    try:
        shutil.copy2(source_path, dest_path)
        return dest_path
    except Exception as e:
        logger.error(f"Error copying file {source_path} to {dest_path}: {e}")
        return None

def export_draft(project_info, shots, static_folder, export_dir):
    """
    生成剪映草稿工程
    """
    if not JIANYING_AVAILABLE:
        return {"success": False, "error": "pyJianYingDraft library not installed."}

    film_name = project_info.get('film_name', 'Untitled_Project')
    # 移除文件名中的非法字符
    film_name = "".join([c for c in film_name if c.isalnum() or c in ' _-']).strip()
    if not film_name: film_name = "Project_Export"
    
    # 确保导出根目录存在
    if not os.path.exists(export_dir):
        os.makedirs(export_dir, exist_ok=True)

    try:
        # 1. 设置草稿文件夹
        draft_folder = draft.DraftFolder(export_dir)
        
        # 2. 创建剪映草稿
        script = draft_folder.create_draft(film_name, 1920, 1080, allow_replace=True)
        
        # 获取草稿的实际物理路径 (pyJianYingDraft 会在 export_dir 下创建同名文件夹)
        draft_sys_path = os.path.join(export_dir, film_name)
        
        # 在草稿内部创建一个 media 文件夹
        assets_target_dir = os.path.join(draft_sys_path, "media")
        
        # 3. 添加轨道
        script.add_track(draft.TrackType.video).add_track(draft.TrackType.audio).add_track(draft.TrackType.text)
        
        current_time = 0.0
        
        for idx, shot in enumerate(shots):
            duration_sec = parse_duration(shot.get('duration', '3s'))
            start_time_str = f"{current_time:.3f}s"
            duration_str = f"{duration_sec:.3f}s"
            
            # trange 参数: (start, duration)
            target_trange = trange(start_time_str, duration_str)
            
            file_prefix = f"{idx+1:03d}_shot"

            # --- 视频轨道 (优先视频 > 首帧) ---
            media_source_path = None
            video_url = shot.get('video_url', '')
            start_frame = shot.get('start_frame', '')
            
            if video_url:
                # 拼接本地路径
                clean_url = video_url.lstrip('/')
                media_source_path = os.path.join(static_folder, clean_url)
            elif start_frame:
                clean_url = start_frame.lstrip('/')
                media_source_path = os.path.join(static_folder, clean_url)
            
            if media_source_path:
                copied_media_path = copy_asset(media_source_path, assets_target_dir, prefix=file_prefix)
                if copied_media_path:
                    # 视频片段
                    segment = draft.VideoSegment(copied_media_path, target_trange)
                    script.add_segment(segment)
            
            # --- 音频轨道 ---
            audio_url = shot.get('audio_url', '')
            if audio_url:
                clean_url = audio_url.lstrip('/')
                abs_audio = os.path.join(static_folder, clean_url)
                copied_audio_path = copy_asset(abs_audio, assets_target_dir, prefix=file_prefix)
                
                if copied_audio_path:
                    # 音频片段
                    audio_seg = draft.AudioSegment(copied_audio_path, target_trange)
                    script.add_segment(audio_seg)
            
            # --- 文本轨道 ---
            text_content = shot.get('dialogue') or shot.get('visual_description')
            if text_content:
                text_seg = draft.TextSegment(text_content, target_trange)
                text_seg.style = draft.TextStyle(color=(1.0, 1.0, 1.0)) 
                script.add_segment(text_seg)

            current_time += duration_sec
            
        # 4. 保存草稿
        script.save()
        
        return {
            "success": True, 
            "message": f"剪映草稿生成成功，素材已打包至 {draft_sys_path}", 
            "path": draft_sys_path
        }

    except Exception as e:
        logger.exception("Export failed")
        return {"success": False, "error": str(e)}