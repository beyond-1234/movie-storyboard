import os
import json
import shutil
import uuid

# 尝试导入 pyJianYingDraft
try:
    import pyJianYingDraft as draft
    from pyJianYingDraft import trange
    JIANYING_AVAILABLE = True
except ImportError:
    JIANYING_AVAILABLE = False
    print("Warning: 'pyJianYingDraft' not found. Please install it via pip.")

def parse_duration(duration_str):
    """解析时长字符串，如 '3s', '3.5'，返回浮点数秒。默认 3.0s"""
    if not duration_str: return 3.0
    try:
        clean = str(duration_str).lower().replace('s', '').strip()
        return float(clean)
    except:
        return 3.0

def copy_asset(source_path, dest_folder, prefix=""):
    """
    复制资源文件到目标目录，并返回新的绝对路径
    :param source_path: 源文件绝对路径
    :param dest_folder: 目标文件夹
    :param prefix: 文件名前缀（防止重名覆盖）
    :return: 新文件的绝对路径
    """
    if not source_path or not os.path.exists(source_path):
        return None
    
    # 确保目标文件夹存在
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
        
    filename = os.path.basename(source_path)
    # 添加前缀防止重名 (例如 shot_1_video.mp4)
    if prefix:
        new_filename = f"{prefix}_{filename}"
    else:
        new_filename = filename
        
    dest_path = os.path.join(dest_folder, new_filename)
    
    # 如果文件已存在，直接返回路径（避免重复复制），或者覆盖
    # 这里选择覆盖或跳过均可，为了简单直接复制
    try:
        shutil.copy2(source_path, dest_path)
        return dest_path
    except Exception as e:
        print(f"Error copying file {source_path}: {e}")
        return None

def export_draft(project_info, shots, static_folder, export_dir):
    """
    生成剪映草稿工程 (包含素材拷贝)
    :param project_info: 项目信息字典
    :param shots: 分镜列表
    :param static_folder: 静态资源根目录 (用于拼接绝对路径)
    :param export_dir: 导出目标目录
    :return: result dict
    """
    if not JIANYING_AVAILABLE:
        return {"success": False, "error": "pyJianYingDraft library not installed."}

    film_name = project_info.get('film_name', 'Untitled_Project')
    # 移除文件名中的非法字符
    film_name = "".join([c for c in film_name if c.isalnum() or c in ' _-']).strip()
    
    # 确保导出根目录存在
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    try:
        # 1. 设置草稿文件夹
        draft_folder = draft.DraftFolder(export_dir)
        
        # 2. 创建剪映草稿
        # 这会在 export_dir 下创建一个名为 film_name 的文件夹
        script = draft_folder.create_draft(film_name, 1920, 1080, allow_replace=True)
        
        # 获取草稿的实际物理路径，用于存放素材
        # pyJianYingDraft 创建的目录名通常就是 film_name
        draft_sys_path = os.path.join(export_dir, film_name)
        
        # 在草稿内部创建一个 media 文件夹，专门存放拷贝过来的素材
        # 结构: exports/MyProject/media/xxx.mp4
        assets_target_dir = os.path.join(draft_sys_path, "media")
        
        # 3. 添加轨道
        script.add_track(draft.TrackType.video).add_track(draft.TrackType.audio).add_track(draft.TrackType.text)
        
        current_time = 0.0
        
        for idx, shot in enumerate(shots):
            duration_sec = parse_duration(shot.get('duration', '3s'))
            start_time_str = f"{current_time:.3f}s"
            duration_str = f"{duration_sec:.3f}s"
            target_trange = trange(start_time_str, duration_str)
            
            # 文件名前缀，方便在文件夹中识别顺序 (e.g., "001_scene1_")
            file_prefix = f"{idx+1:03d}_shot"

            # --- 视频轨道 (优先视频 > 首帧) ---
            media_source_path = None
            
            if shot.get('video_url'):
                rel_path = shot.get('video_url').lstrip('/')
                abs_path = os.path.abspath(os.path.join(static_folder, rel_path))
                if os.path.exists(abs_path):
                    media_source_path = abs_path
            
            if not media_source_path and shot.get('start_frame'):
                rel_path = shot.get('start_frame').lstrip('/')
                abs_path = os.path.abspath(os.path.join(static_folder, rel_path))
                if os.path.exists(abs_path):
                    media_source_path = abs_path
            
            if media_source_path:
                # 核心修改：复制文件到草稿目录
                # 复制后的路径用于添加到剪映脚本
                copied_media_path = copy_asset(media_source_path, assets_target_dir, prefix=file_prefix)
                
                if copied_media_path:
                    segment = draft.VideoSegment(copied_media_path, target_trange)
                    script.add_segment(segment)
            
            # --- 音频轨道 ---
            if shot.get('audio_url'):
                rel_audio = shot.get('audio_url').lstrip('/')
                abs_audio = os.path.abspath(os.path.join(static_folder, rel_audio))
                
                # 核心修改：复制音频文件
                copied_audio_path = copy_asset(abs_audio, assets_target_dir, prefix=file_prefix)
                
                if copied_audio_path:
                    audio_seg = draft.AudioSegment(copied_audio_path, target_trange)
                    script.add_segment(audio_seg)
            
            # --- 文本轨道 ---
            text_content = shot.get('dialogue') or shot.get('visual_description')
            if text_content:
                text_seg = draft.TextSegment(text_content, target_trange)
                text_seg.style = draft.TextStyle(color=(1.0, 1.0, 1.0)) 
                script.add_segment(text_seg)

            # 更新时间游标
            current_time += duration_sec
            
        # 4. 保存草稿
        script.save()
        
        return {
            "success": True, 
            "message": f"剪映草稿生成成功，所有素材已打包至 {draft_sys_path}", 
            "path": draft_sys_path
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}