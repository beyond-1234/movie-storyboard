import os
import json
import uuid
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

# --- 配置常量 ---
DATA_DIR = "projects"
SETTINGS_FILE = "settings.json"
SERIES_FILE = "series.json"

# --- 数据模型 (Data Models) ---
@dataclass
class Series:
    id: str
    name: str
    description: str = ""
    cover_image: str = ""
    script_core_conflict: str = ""
    script_emotional_keywords: str = ""
    basic_info: str = "" 
    visual_color_system: str = ""
    visual_consistency_prompt: str = ""
    created_time: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    def to_dict(self): return asdict(self)

@dataclass
class MovieProject:
    film_name: str
    script_core_conflict: str = ""
    series_id: str = ""
    script_emotional_keywords: str = ""
    basic_info: str = ""
    visual_color_system: str = ""
    visual_consistency_prompt: str = "" 
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_time: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def from_dict(cls, data): 
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    def to_dict(self): return asdict(self)

@dataclass
class StoryboardShot:
    movie_id: str
    scene: str
    shot_number: str
    visual_description: str
    scene_description: str = ""
    scene_prompt: str = ""
    scene_image: str = ""
    characters: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    audio_description: str = ""
    special_technique: str = ""
    duration: str = ""
    notes: str = ""
    start_frame: str = ""
    end_frame: str = ""
    video_url: str = "" 
    dialogue: str = "" 
    audio_url: str = "" 
    start_frame_prompt: str = ""
    end_frame_prompt: str = ""
    images: List[str] = field(default_factory=list) 
    created_time: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def from_dict(cls, data): 
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    def to_dict(self): return asdict(self)

@dataclass
class FusionTask:
    id: str
    scene: str
    shot_number: str
    base_image: str = ""
    elements: List[Dict] = field(default_factory=list)
    result_image: str = ""
    fusion_prompt: str = ""
    end_frame_image: str = ""
    end_frame_prompt: str = ""
    shot_id: str = ""
    video_url: str = ""
    scene_description: str = ""  # 场景说明
    visual_description: str = "" # 画面描述
    dialogue: str = ""           # 对白
    audio_description: str = ""  # 声音描述
    created_time: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def from_dict(cls, data): return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    def to_dict(self): return asdict(self)


class DataManager:
    def __init__(self):
        self._ensure_root_dirs()

    # --- 基础工具 ---
    def _ensure_root_dirs(self):
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

    def _read_json(self, filepath, default=None):
        if not os.path.exists(filepath): return default if default is not None else {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default if default is not None else {}

    def _write_json(self, filepath, data):
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        def json_serial(obj):
            if isinstance(obj, datetime): return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        with open(filepath, 'w', encoding='utf-8') as f: 
            json.dump(data, f, default=json_serial, indent=4, ensure_ascii=False)

    def _get_project_path(self, pid):
        return os.path.join(DATA_DIR, pid)

    # --- Series (剧集) CRUD ---
    def get_all_series(self):
        series_list = self._read_json(SERIES_FILE, default=[])
        series_list.sort(key=lambda x: x.get('updated_time', ''), reverse=True)
        return series_list

    def get_series_by_id(self, series_id):
        series_list = self.get_all_series()
        return next((s for s in series_list if s['id'] == series_id), None)

    def create_series(self, data):
        series_list = self._read_json(SERIES_FILE, default=[])
        data['id'] = str(uuid.uuid4())
        new_series = Series.from_dict(data)
        series_list.insert(0, new_series.to_dict())
        self._write_json(SERIES_FILE, series_list)
        return new_series.to_dict()

    def update_series(self, series_id, data):
        series_list = self._read_json(SERIES_FILE, default=[])
        for i, s in enumerate(series_list):
            if s['id'] == series_id:
                merged = {**s, **data, 'updated_time': datetime.now().isoformat()}
                series_list[i] = merged
                self._write_json(SERIES_FILE, series_list)
                return merged
        return None

    def delete_series(self, series_id):
        series_list = self._read_json(SERIES_FILE, default=[])
        new_list = [s for s in series_list if s['id'] != series_id]
        self._write_json(SERIES_FILE, new_list)
        return True

    # --- Settings (设置) CRUD ---
    def get_settings(self):
        return self._read_json(SETTINGS_FILE, default={'providers': []})

    def save_settings(self, settings_data):
        self._write_json(SETTINGS_FILE, settings_data)

    def get_provider_config(self, provider_id):
        settings = self.get_settings()
        for p in settings.get('providers', []):
            if p.get('id') == provider_id: return p
        return {'type': 'mock'}

    # --- Project (项目/分集) CRUD ---
    def get_all_projects(self):
        projects = []
        if os.path.exists(DATA_DIR):
            for pid in os.listdir(DATA_DIR):
                info_path = os.path.join(self._get_project_path(pid), 'info.json')
                if os.path.exists(info_path): 
                    projects.append(self._read_json(info_path))
        projects.sort(key=lambda x: x.get('updated_time', ''), reverse=True)
        return projects

    def get_projects_by_series(self, series_id):
        # 获取所有项目并筛选
        all_projs = self.get_all_projects()
        filtered = [p for p in all_projs if p.get('series_id') == series_id]
        filtered.sort(key=lambda x: x.get('created_time', ''))
        return filtered

    def get_project(self, project_id):
        path = os.path.join(self._get_project_path(project_id), 'info.json')
        return self._read_json(path)

    def create_project(self, data):
        project = MovieProject.from_dict(data)
        proj_dir = self._get_project_path(project.id)
        
        # 初始化文件结构
        self._write_json(os.path.join(proj_dir, 'info.json'), project.to_dict())
        self._write_json(os.path.join(proj_dir, 'shot.json'), [])
        self._write_json(os.path.join(proj_dir, 'script.json'), [])
        self._write_json(os.path.join(proj_dir, 'characters.json'), [])
        self._write_json(os.path.join(proj_dir, 'fusions.json'), [])
        
        return project.to_dict()

    def update_project(self, project_id, data):
        path = os.path.join(self._get_project_path(project_id), 'info.json')
        current = self._read_json(path)
        if not current: return None
        new_data = {**current, **data, 'id': project_id, 'updated_time': datetime.now().isoformat()}
        self._write_json(path, new_data)
        return new_data

    def delete_project(self, project_id):
        path = self._get_project_path(project_id)
        if os.path.exists(path):
            shutil.rmtree(path)
            return True
        return False

    # --- Script (剧本) CRUD ---
    def get_script(self, project_id):
        return self._read_json(os.path.join(self._get_project_path(project_id), 'script.json'), default=[])

    def save_script(self, project_id, script_data):
        self._write_json(os.path.join(self._get_project_path(project_id), 'script.json'), script_data)

    # --- Shot (分镜) CRUD ---
    def get_shots(self, project_id):
        return self._read_json(os.path.join(self._get_project_path(project_id), 'shot.json'), default=[])

    def get_shot(self, project_id, shot_id):
        shots = self.get_shots(project_id)
        return next((s for s in shots if s['id'] == shot_id), None)
        
    def get_previous_shot(self, project_id, current_shot_number):
        shots = self.get_shots(project_id)
        # 假设 shot_number 是数字类型，如果是字符串需要转换
        try:
            curr_num = int(current_shot_number)
            return next((s for s in shots if int(s['shot_number']) == curr_num - 1), None)
        except:
            return None

    def create_shot(self, project_id, data):
        shots = self.get_shots(project_id)
        new_shot = StoryboardShot.from_dict({**data, 'movie_id': project_id})
        
        insert_index = data.get('insert_index')
        if insert_index is not None and isinstance(insert_index, int) and 0 <= insert_index <= len(shots):
            shots.insert(insert_index, new_shot.to_dict())
        else:
            shots.append(new_shot.to_dict())
            
        self._write_json(os.path.join(self._get_project_path(project_id), 'shot.json'), shots)
        return new_shot.to_dict()

    def update_shot(self, project_id, shot_id, data):
        path = os.path.join(self._get_project_path(project_id), 'shot.json')
        shots = self._read_json(path, default=[])
        updated_shot = None
        for i, s in enumerate(shots):
            if s['id'] == shot_id:
                merged_data = {**s, **data, 'id': shot_id, 'updated_time': datetime.now().isoformat()}
                new_shot = StoryboardShot.from_dict(merged_data)
                shots[i] = new_shot.to_dict()
                updated_shot = shots[i]
                break
        
        if updated_shot:
            self._write_json(path, shots)
        return updated_shot

    def delete_shot(self, project_id, shot_id):
        path = os.path.join(self._get_project_path(project_id), 'shot.json')
        shots = self._read_json(path, default=[])
        new_shots = [s for s in shots if s['id'] != shot_id]
        self._write_json(path, new_shots)
        return True

    def batch_delete_shots(self, project_id, shot_ids):
        path = os.path.join(self._get_project_path(project_id), 'shot.json')
        shots = self._read_json(path, default=[])
        new_shots = [s for s in shots if s['id'] not in shot_ids]
        self._write_json(path, new_shots)

    def reorder_shots(self, project_id, ordered_ids):
        path = os.path.join(self._get_project_path(project_id), 'shot.json')
        shots = self._read_json(path, default=[])
        shot_map = {s['id']: s for s in shots}
        new_shots = [shot_map[sid] for sid in ordered_ids if sid in shot_map]
        # 添加不在 ordered_ids 中的剩余 shot（防止数据丢失）
        existing_ids = set(ordered_ids)
        new_shots.extend([s for s in shots if s['id'] not in existing_ids])
        self._write_json(path, new_shots)

    # --- Characters (角色) CRUD ---
    def get_characters(self, project_id):
        return self._read_json(os.path.join(self._get_project_path(project_id), 'characters.json'), default=[])

    def create_character(self, project_id, data):
        path = os.path.join(self._get_project_path(project_id), 'characters.json')
        characters = self._read_json(path, default=[])
        new_char = {
            'id': str(uuid.uuid4()),
            'name': data.get('name'),
            'description': data.get('description'),
            'image_url': data.get('image_url', ''),
            'created_time': datetime.now().isoformat()
        }
        characters.append(new_char)
        self._write_json(path, characters)
        return new_char

    def update_character(self, project_id, character_id, data):
        path = os.path.join(self._get_project_path(project_id), 'characters.json')
        characters = self._read_json(path, default=[])
        updated_char = None
        for i, char in enumerate(characters):
            if char['id'] == character_id:
                updated_char = {**char, **data}
                characters[i] = updated_char
                break
        if updated_char:
            self._write_json(path, characters)
        return updated_char

    def delete_character(self, project_id, character_id):
        path = os.path.join(self._get_project_path(project_id), 'characters.json')
        characters = self._read_json(path, default=[])
        new_characters = [c for c in characters if c['id'] != character_id]
        self._write_json(path, new_characters)

    # --- Fusion Tasks (融图) CRUD ---
    def get_fusions(self, project_id):
        return self._read_json(os.path.join(self._get_project_path(project_id), 'fusions.json'), default=[])

    def create_fusion(self, project_id, data):
        path = os.path.join(self._get_project_path(project_id), 'fusions.json')
        fusions = self._read_json(path, default=[])
        
        data['id'] = str(uuid.uuid4())
        data['created_time'] = datetime.now().isoformat()
        data['updated_time'] = datetime.now().isoformat()
        
        new_fusion = FusionTask.from_dict(data)
        
        insert_index = data.get('insert_index')
        if insert_index is not None and isinstance(insert_index, int) and 0 <= insert_index <= len(fusions):
            fusions.insert(insert_index, new_fusion.to_dict())
        else:
            fusions.append(new_fusion.to_dict())
            
        self._write_json(path, fusions)
        return new_fusion.to_dict()

    def update_fusion(self, project_id, fusion_id, data):
        path = os.path.join(self._get_project_path(project_id), 'fusions.json')
        fusions = self._read_json(path, default=[])
        updated_fusion = None
        for i, f in enumerate(fusions):
            if f['id'] == fusion_id:
                merged = {**f, **data, 'id': fusion_id, 'updated_time': datetime.now().isoformat()}
                new_fusion = FusionTask.from_dict(merged)
                fusions[i] = new_fusion.to_dict()
                updated_fusion = fusions[i]
                break
        
        if updated_fusion:
            self._write_json(path, fusions)
        return updated_fusion
        
    def get_fusion(self, project_id, fusion_id):
        fusions = self.get_fusions(project_id)
        return next((f for f in fusions if f['id'] == fusion_id), None)

    def delete_fusion(self, project_id, fusion_id):
        path = os.path.join(self._get_project_path(project_id), 'fusions.json')
        fusions = self._read_json(path, default=[])
        new_fusions = [f for f in fusions if f['id'] != fusion_id]
        self._write_json(path, new_fusions)
        return True