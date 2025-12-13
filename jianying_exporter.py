import os
import json
import shutil
import uuid
import logging
from urllib.parse import unquote, urlparse # 新增：用于处理URL解码

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
    """解析时长字符串"""
    if not duration_str: return 3.0
    try:
        clean = str(duration_str).lower().replace('s', '').strip()
        val = float(clean)
        return val if val > 0 else 3.0
    except:
        return 3.0

def resolve_local_path(static_folder, url_path):
    """
    【核心修复】将网页URL转换为本地绝对路径
    1. 解码 URL (处理空格 %20 等)
    2. 去除 http/https 前缀
    3. 拼接 static_folder
    """
    if not url_path:
        return None
        
    # 1. 解码: "/uploads/image%201.png" -> "/uploads/image 1.png"
    path = unquote(str(url_path))
    
    # 2. 如果是完整 URL (http://localhost...), 只取路径部分
    if path.startswith('http'):
        parsed = urlparse(path)
        path = parsed.path # 只取 /uploads/xxx
        
    # 3. 去除开头的斜杠，防止 os.path.join 把它当做绝对路径处理
    # Windows下也要去除反斜杠
    path = path.lstrip('/\\')
    
    # 4. 拼接绝对路径
    full_path = os.path.join(static_folder, path)
    abs_path = os.path.abspath(full_path)
    
    return abs_path

def copy_asset(source_full_path, dest_folder, prefix=""):
    """
    复制资源文件
    """
    if not source_full_path:
        return None
        
    # --- 调试打印 ---
    # 如果控制台打印了 "❌ 未找到文件"，说明路径拼错了
    if not os.path.exists(source_full_path):
        print(f"❌ [文件缺失] 试图寻找: {source_full_path}") 
        return None
    
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder, exist_ok=True)
        
    filename = os.path.basename(source_full_path)
    clean_filename = "".join([c for c in filename if c.isalnum() or c in '._-'])
    
    if prefix:
        new_filename = f"{prefix}_{clean_filename}"
    else:
        new_filename = clean_filename
        
    dest_path = os.path.join(dest_folder, new_filename)
    
    try:
        shutil.copy2(source_full_path, dest_path)
        print(f"✅ [复制成功] {new_filename}") # 打印成功信息
        return dest_path
    except Exception as e:
        print(f"❌ [复制出错] {e}")
        return None

def export_draft(project_info, tasks, static_folder, export_dir): 
    # 注意：这里第二个参数名我改成了 tasks，代表传入的是 fusion 列表
    """
    生成剪映草稿工程 (适配 Fusion 数据源)
    """
    if not JIANYING_AVAILABLE:
        return {"success": False, "error": "pyJianYingDraft library not installed."}

    film_name = project_info.get('film_name', 'Untitled_Project')
    film_name = "".join([c for c in film_name if c.isalnum() or c in ' _-']).strip()
    if not film_name: film_name = "Project_Export"
    
    if not os.path.exists(export_dir):
        os.makedirs(export_dir, exist_ok=True)

    try:
        # 1. 准备目录
        draft_folder = draft.DraftFolder(export_dir)
        script = draft_folder.create_draft(film_name, 1920, 1080, allow_replace=True)
        draft_sys_path = os.path.join(export_dir, film_name)
        assets_target_dir = os.path.join(draft_sys_path, "media")
        os.makedirs(assets_target_dir, exist_ok=True)
        
        # 2. 轨道设置
        script.add_track(draft.TrackType.video).add_track(draft.TrackType.audio).add_track(draft.TrackType.text)
        
        current_time = 0.0
        
        print(f"========== 开始导出 (Fusion 模式) ==========")
        print(f"数据源数量: {len(tasks)}")

        for idx, item in enumerate(tasks):
            # item 现在是一个 fusion 对象
            
            # === 调试打印 ===
            scene = item.get('scene', '?')
            shot_no = item.get('shot_number', '?')
            print(f"--- 处理第 {idx+1} 项: 场{scene}-镜{shot_no} ---")
            
            # === 字段适配 (关键修改) ===
            # Fusion 对象通常包含：
            # - video_url: 生成的视频
            # - result_image: 融图生成的最终图片
            # - base_image: 底图 (备选)
            raw_url = item.get('video_url') or ''
            
            # 打印一下找到的路径，方便你调试
            print(f"   关键字段 video_url: {item.get('video_url')}")
            print(f"   关键字段 result_image: {item.get('result_image')}")
            print(f"   👉 最终决定使用: {raw_url}")

            # 时长 (Fusion 如果没有 duration 字段，默认 3s)
            duration_sec = parse_duration(item.get('duration', '3s'))
            start_time_str = f"{current_time:.3f}s"
            duration_str = f"{duration_sec:.3f}s"
            target_trange = trange(start_time_str, duration_str)
            file_prefix = f"{idx+1:03d}_sc{scene}_sh{shot_no}" # 文件名前缀带上场号镜号方便识别

            # === 视频/图片处理逻辑 (使用 resolve_local_path) ===
            media_source_path = resolve_local_path(static_folder, raw_url)
            
            if media_source_path and os.path.exists(media_source_path):
                copied_path = copy_asset(media_source_path, assets_target_dir, prefix=file_prefix)
                if copied_path:
                    segment = draft.VideoSegment(copied_path, target_trange)
                    script.add_segment(segment)
            else:
                print(f"   ⚠️ 跳过: 文件不存在或路径为空 -> {media_source_path}")

            # === 文本 (Fusion 可能没有 dialogue，看你需求) ===
            # 如果想显示 Prompt 作为字幕，可以用 item.get('fusion_prompt')
            text_content = item.get('dialogue') or item.get('fusion_prompt')
            if text_content:
                text_seg = draft.TextSegment(text_content, target_trange)
                text_seg.style = draft.TextStyle(color=(1.0, 1.0, 1.0)) 
                script.add_segment(text_seg)

            current_time += duration_sec
            
        script.save()
        
        zip_output_name = os.path.join(export_dir, f"{film_name}_archive")
        shutil.make_archive(zip_output_name, 'zip', export_dir, film_name)
        
        return {
            "success": True, 
            "message": "打包成功", 
            "zip_path": zip_output_name + ".zip",
            "folder_path": draft_sys_path
        }

    except Exception as e:
        logger.exception("Export failed")
        return {"success": False, "error": str(e)}