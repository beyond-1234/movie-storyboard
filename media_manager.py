import os
import re
import uuid
import mimetypes
import logging
import base64
import requests
from pathlib import Path
from urllib.parse import urlparse
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MediaManager")

class MediaManager:
    def __init__(self, static_folder="."):
        self.static_folder = static_folder
        self.dirs = {
            'image': "static/imgs",
            'video': "static/videos",
            'audio': "static/audio",
            'export': "exports",
            'temp': "static/temp"
        }
        self._ensure_dirs()

    def _ensure_dirs(self):
        """初始化目录结构"""
        for d in self.dirs.values():
            path = os.path.join(self.static_folder, d)
            Path(path).mkdir(parents=True, exist_ok=True)

    def _get_directory(self, media_type):
        return os.path.join(self.static_folder, self.dirs.get(media_type, 'static/temp'))

    def _get_web_path(self, media_type, filename):
        """返回前端可访问的相对路径"""
        dir_path = self.dirs.get(media_type, 'static/temp')
        # 统一使用正斜杠，适配Web
        return f"/{dir_path}/{filename}".replace("\\", "/")

    def _generate_versioned_filename(self, directory, entity_id, extension):
        """
        生成带有版本号的文件名
        策略: 
        - 如果没有 entity_id，使用 UUID。
        - 如果有 entity_id，查找目录下匹配 {entity_id}_v{N}{ext} 的文件，N自增。
        """
        if not entity_id:
            return f"{uuid.uuid4()}{extension}"

        # 清洗文件名，防止非法字符
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(entity_id))
        if not safe_id: # 如果清洗后为空
            return f"{uuid.uuid4()}{extension}"

        # 匹配模式: entityId_v1.png, entityId_v2.mp4
        # 注意：这里我们只匹配当前扩展名的文件版本，不同扩展名(如png和jpg)互不影响版本号
        # 或者可以设计为忽略扩展名版本，这里采用匹配扩展名
        pattern = re.compile(rf"^{re.escape(safe_id)}_v(\d+){re.escape(extension)}$")
        
        max_version = 0
        if os.path.exists(directory):
            for f in os.listdir(directory):
                match = pattern.match(f)
                if match:
                    try:
                        v = int(match.group(1))
                        if v > max_version:
                            max_version = v
                    except ValueError:
                        continue
        
        new_version = max_version + 1
        return f"{safe_id}_v{new_version}{extension}"

    def get_absolute_path(self, relative_path):
        """将Web路径转换为绝对文件系统路径"""
        if not relative_path: return None
        # 去掉开头的 /
        clean_path = relative_path.lstrip('/')
        return os.path.abspath(os.path.join(self.static_folder, clean_path))

    def save_uploaded_file(self, file_obj, media_type='image', entity_id=None):
        """保存 Flask 上传的文件对象"""
        if not file_obj or not file_obj.filename:
            return None, "No file provided"
        
        # 获取扩展名
        ext = os.path.splitext(file_obj.filename)[1].lower()
        if not ext:
            ext = '.png' if media_type == 'image' else '.mp4'

        directory = self._get_directory(media_type)
        filename = self._generate_versioned_filename(directory, entity_id, ext)
        save_path = os.path.join(directory, filename)
        
        try:
            file_obj.save(save_path)
            logger.info(f"Saved upload: {save_path}")
            return self._get_web_path(media_type, filename), None
        except Exception as e:
            logger.error(f"Upload save failed: {e}")
            return None, str(e)

    def download_from_url(self, url, media_type='image', entity_id=None):
        """从 URL 下载文件并保存"""
        try:
            # 尝试从URL推断扩展名
            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[1].lower()
            if not ext or len(ext) > 5: # 简单的校验
                # 默认扩展名
                if media_type == 'image': ext = '.png'
                elif media_type == 'video': ext = '.mp4'
                elif media_type == 'audio': ext = '.mp3'
            
            directory = self._get_directory(media_type)
            filename = self._generate_versioned_filename(directory, entity_id, ext)
            save_path = os.path.join(directory, filename)
            
            logger.info(f"Downloading {url} -> {save_path}")
            
            resp = requests.get(url, stream=True, timeout=120)
            if resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                return self._get_web_path(media_type, filename)
            else:
                logger.error(f"Download failed with status: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Download exception: {e}")
            return None

    def save_binary(self, binary_data, media_type='image', entity_id=None, extension=None):
        """保存二进制数据"""
        if not binary_data: return None
        
        if not extension:
            if media_type == 'image': extension = '.png'
            elif media_type == 'video': extension = '.mp4'
            elif media_type == 'audio': extension = '.mp3'
            
        directory = self._get_directory(media_type)
        filename = self._generate_versioned_filename(directory, entity_id, extension)
        save_path = os.path.join(directory, filename)
        
        try:
            with open(save_path, 'wb') as f:
                f.write(binary_data)
            return self._get_web_path(media_type, filename)
        except Exception as e:
            logger.error(f"Binary save failed: {e}")
            return None

    def file_to_base64(self, web_path_or_local_path):
        """读取文件并转换为 Base64 (Data URI Scheme)"""
        if not web_path_or_local_path: return None
        
        # 转换为本地绝对路径
        if web_path_or_local_path.startswith('http'):
            # 如果是远程URL，暂不支持直接转base64，或者需要下载
            return None 
            
        local_path = self.get_absolute_path(web_path_or_local_path)
        
        if not os.path.exists(local_path):
            logger.warning(f"File not found for base64: {local_path}")
            return None
            
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type: mime_type = 'application/octet-stream'
        
        try:
            with open(local_path, "rb") as f:
                base64_data = base64.b64encode(f.read()).decode('utf-8')
            return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            logger.error(f"Base64 conversion failed: {e}")
            return None

    def scan_project_files(self, entity_map):
        """
        扫描整个项目相关的历史文件
        :param entity_map: 字典 { entity_id: { 'name': 'xxx', 'type': 'character/scene/fusion' } }
        """
        history_items = []
        
        # 需要扫描的目录类型
        target_types = ['image', 'video', 'audio']
        
        for media_type in target_types:
            directory = self._get_directory(media_type)
            if not os.path.exists(directory):
                continue
                
            # 获取所有文件
            files = os.listdir(directory)
            
            # 匹配文件名：ID_v版本.后缀 (例如: uuid123_v1.png)
            # 或者 ID.后缀 (无版本号的也算v0或最新)
            version_pattern = re.compile(r"^(.+?)_v(\d+)\.(.+)$")
            
            for f in files:
                # 跳过隐藏文件
                if f.startswith('.'): continue
                
                file_path = os.path.join(directory, f)
                
                # 尝试匹配带版本的
                match = version_pattern.match(f)
                entity_id = None
                version = 1
                
                if match:
                    entity_id = match.group(1)
                    version = int(match.group(2))
                else:
                    # 尝试匹配不带版本的 (作为当前版本)
                    base_name = os.path.splitext(f)[0]
                    # 简单的清理逻辑，如果 ID 包含非法字符可能需要更复杂的匹配，这里假设 ID 比较纯净
                    if base_name in entity_map:
                        entity_id = base_name
                        version = 9999 # 标记为当前/最新
                
                # 如果这个文件的 ID 属于当前项目
                if entity_id and entity_id in entity_map:
                    entity_info = entity_map[entity_id]
                    file_stat = os.stat(file_path)
                    
                    history_items.append({
                        'filename': f,
                        'url': self._get_web_path(media_type, f),
                        'entity_id': entity_id,
                        'entity_name': entity_info.get('name', '未知'),
                        'entity_type': entity_info.get('type', 'unknown'),
                        'media_type': media_type,
                        'version': version,
                        'timestamp': file_stat.st_mtime, # 修改时间
                        'date_str': time.strftime('%Y-%m-%d %H:%M', time.localtime(file_stat.st_mtime))
                    })
        
        # 按时间倒序排列（最新的在前面）
        history_items.sort(key=lambda x: x['timestamp'], reverse=True)
        return history_items