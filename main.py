import os
import json
import uuid
import time
import re
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from flask import Flask, request, jsonify, send_file
from pathlib import Path

import ai_service 
from jianying_exporter import export_draft

# --- 配置 ---
DATA_DIR = "projects"
STATIC_FOLDER = "."
IMG_SAVE_DIR = "static/imgs"
VIDEO_SAVE_DIR = "static/videos"
AUDIO_SAVE_DIR = "static/audio"
SETTINGS_FILE = "settings.json"
EXPORT_DIR = "exports"

app = Flask(__name__, static_url_path='', static_folder=STATIC_FOLDER)

# --- 基础工具 ---
def ensure_dirs():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    for d in [IMG_SAVE_DIR, VIDEO_SAVE_DIR, AUDIO_SAVE_DIR, EXPORT_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)

def get_project_path(pid): return os.path.join(DATA_DIR, pid)

def read_json(filepath, default=None):
    if not os.path.exists(filepath): return default if default is not None else {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
    except: return default if default is not None else {}

def write_json(filepath, data):
    # 修复：只有当路径包含目录时才创建目录，防止 Windows 下 os.makedirs('') 报错
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
        
    def json_serial(obj):
        if isinstance(obj, datetime): return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, default=json_serial, indent=4, ensure_ascii=False)

def get_provider_config(provider_id):
    settings = read_json(SETTINGS_FILE, default={'providers': []})
    for p in settings.get('providers', []):
        if p.get('id') == provider_id: return p
    return {'type': 'mock'} 

# --- 数据模型 ---
@dataclass
class MovieProject:
    film_name: str
    script_core_conflict: str = ""
    script_emotional_keywords: str = ""
    # 合并世界观设定的三个字段为一个基础信息字段
    basic_info: str = ""  # 包含时代背景、空间特质、人物小传
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
    # 场景相关字段
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

# --- 路由 ---
@app.route('/')
def index(): return send_file('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    data = read_json(SETTINGS_FILE, default={'providers': []})
    for p in data.get('providers', []):
        if p.get('api_key'): p['api_key'] = p['api_key'][:6] + '******'
    return jsonify(data.get('providers', []))

@app.route('/api/settings/provider', methods=['POST'])
def save_provider():
    req = request.json
    settings = read_json(SETTINGS_FILE, default={'providers': []})
    providers = settings.get('providers', [])
    
    new_p = {
        'id': req.get('id') or str(uuid.uuid4()),
        'name': req.get('name', 'New Provider'),
        'type': req.get('type', 'aliyun'),
        'base_url': req.get('base_url', ''),
        'models': req.get('models', []),
        'enabled': req.get('enabled', True)
    }
    
    input_key = req.get('api_key', '')
    existing = next((p for p in providers if p['id'] == new_p['id']), None)
    
    if existing:
        new_p['api_key'] = existing.get('api_key', '') if '******' in input_key else input_key
        for i, p in enumerate(providers):
            if p['id'] == new_p['id']: providers[i] = new_p
    else:
        new_p['api_key'] = input_key
        providers.append(new_p)
        
    settings['providers'] = providers
    write_json(SETTINGS_FILE, settings)
    return jsonify({"success": True, "id": new_p['id']})

@app.route('/api/settings/provider/<pid>', methods=['DELETE'])
def delete_provider(pid):
    settings = read_json(SETTINGS_FILE)
    settings['providers'] = [p for p in settings.get('providers', []) if p['id'] != pid]
    write_json(SETTINGS_FILE, settings)
    return jsonify({"success": True})

# Project CRUD
@app.route('/api/projects', methods=['GET'])
def get_projects():
    ensure_dirs()
    projects = []
    if os.path.exists(DATA_DIR):
        for pid in os.listdir(DATA_DIR):
            info_path = os.path.join(DATA_DIR, pid, 'info.json')
            if os.path.exists(info_path): projects.append(read_json(info_path))
    projects.sort(key=lambda x: x.get('updated_time', ''), reverse=True)
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    if not data.get('film_name'): return jsonify({"error": "项目名称必填"}), 400
    project = MovieProject.from_dict(data)
    write_json(os.path.join(get_project_path(project.id), 'info.json'), project.to_dict())
    write_json(os.path.join(get_project_path(project.id), 'shot.json'), [])
    write_json(os.path.join(get_project_path(project.id), 'script.json'), [])
    return jsonify(project.to_dict()), 201

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    data = read_json(os.path.join(get_project_path(project_id), 'info.json'))
    return jsonify(data) if data else (jsonify({"error": "Not found"}), 404)

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    path = os.path.join(get_project_path(project_id), 'info.json')
    data = read_json(path)
    if not data: return jsonify({"error": "Not found"}), 404
    new_data = {**data, **request.json, 'id': project_id, 'updated_time': datetime.now().isoformat()}
    write_json(path, new_data)
    return jsonify(new_data)

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    import shutil
    if os.path.exists(get_project_path(project_id)): shutil.rmtree(get_project_path(project_id)); return jsonify({"message": "Deleted"})
    return jsonify({"error": "Not found"}), 404

# Script CRUD
@app.route('/api/projects/<project_id>/script', methods=['GET'])
def get_script(project_id): return jsonify(read_json(os.path.join(get_project_path(project_id), 'script.json'), default=[]))

@app.route('/api/projects/<project_id>/script', methods=['POST'])
def save_script(project_id):
    write_json(os.path.join(get_project_path(project_id), 'script.json'), request.json)
    return jsonify({"success": True})

# Shot CRUD
@app.route('/api/projects/<project_id>/shots', methods=['GET'])
def get_shots(project_id): return jsonify(read_json(os.path.join(get_project_path(project_id), 'shot.json'), default=[]))

@app.route('/api/projects/<project_id>/shots', methods=['POST'])
def create_shot(project_id):
    data = request.json
    shots = read_json(os.path.join(get_project_path(project_id), 'shot.json'), default=[])
    new_shot = StoryboardShot.from_dict({**data, 'movie_id': project_id})
    shots.append(new_shot.to_dict())
    write_json(os.path.join(get_project_path(project_id), 'shot.json'), shots)
    return jsonify(new_shot.to_dict()), 201

@app.route('/api/projects/<project_id>/shots/<shot_id>', methods=['PUT'])
def update_shot(project_id, shot_id):
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])
    for i, s in enumerate(shots):
        if s['id'] == shot_id:
            merged_data = {**s, **request.json, 'id': shot_id, 'updated_time': datetime.now().isoformat()}
            new_shot = StoryboardShot.from_dict(merged_data)
            shots[i] = new_shot.to_dict()
            write_json(path, shots)
            return jsonify(new_shot.to_dict())
    return jsonify({"error": "Not found"}), 404

@app.route('/api/projects/<project_id>/shots/<shot_id>', methods=['DELETE'])
def delete_shot(project_id, shot_id):
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])
    new_shots = [s for s in shots if s['id'] != shot_id]
    write_json(path, new_shots)
    return jsonify({"message": "Deleted"})

@app.route('/api/projects/<project_id>/shots/batch_delete', methods=['POST'])
def batch_delete_shots(project_id):
    ids = request.json.get('ids', [])
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])
    new_shots = [s for s in shots if s['id'] not in ids]
    write_json(path, new_shots)
    return jsonify({"success": True})

@app.route('/api/projects/<project_id>/shots/reorder', methods=['POST'])
def reorder_shots(project_id):
    ordered_ids = request.json.get('shot_ids', [])
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])
    shot_map = {s['id']: s for s in shots}
    new_shots = [shot_map[sid] for sid in ordered_ids if sid in shot_map]
    new_shots.extend([s for s in shots if s['id'] not in ordered_ids])
    write_json(path, new_shots)
    return jsonify({"success": True})

# === AI & Export (Updated for Text Model) ===

@app.route('/api/generate/script_continuation', methods=['POST'])
def generate_script_continuation():
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    # 允许前端覆盖模型
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    sys = "你是一个专业的中文电影编剧助手。请根据前文续写一段剧本。要求：全中文，画面感强。"
    msgs = [{'role': 'system', 'content': sys}, {'role': 'user', 'content': f"前文：\n{data.get('context_text','')}\n\n请续写："}]
    
    result = ai_service.run_text_generation(msgs, config)
    return jsonify(result) if result.get('success') else (jsonify(result), 500)

@app.route('/api/generate/analyze_script', methods=['POST'])
def analyze_script():
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    # 允许前端覆盖模型
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    # 获取项目信息和角色列表
    project_id = data.get('project_id')
    project_info = {}
    character_list = []
    
    if project_id:
        project_info = read_json(os.path.join(get_project_path(project_id), 'info.json'), default={})
        character_list = read_json(os.path.join(get_project_path(project_id), 'characters.json'), default=[])
    
    # 构建角色信息字符串，供AI参考
    characters_info = ""
    if character_list:
        characters_info = "\n".join([f"- {char.get('name', '')}: {char.get('description', '')}" for char in character_list])
        characters_info = f"\n\n已有角色列表：\n{characters_info}"
    
    # 获取项目基础信息
    basic_info = project_info.get('basic_info', '')
    emotional_keywords = project_info.get('script_emotional_keywords', '')
    color_system = project_info.get('visual_color_system', '')
    
    # 构建系统提示词
    sys = f"""
    你是一个专业的电影分镜设计师。请根据剧本内容，生成详细的分镜列表，每个分镜包含场景说明和角色信息。
    **输出要求**：1. 返回一个纯 JSON 数组。2. **必须使用中文**填写所有描述性字段。3. 不要包含 Markdown 标记。
     **JSON对象结构**：
        1. scene: 场次编号
        2. shot_number: 镜号
        3. visual_description: 画面描述
        4. scene_description: 场景说明（详细描述场景环境、时间、地点等）
        5. characters: 出席角色列表（从已有角色中选择，或根据剧本内容推断新角色）
        6. dialogue: 台词（如果有）
        7. audio_description: 声音描述
        8. special_technique: 特殊拍摄技巧
        9. duration: 预计时长
    """
    
    # 构建用户提示词
    user_prompt = f"""
        剧本内容：{data.get('content', '')}
        人物信息：{characters_info}
        项目基础信息：{basic_info}
        情感关键词：{emotional_keywords}
        色彩体系：{color_system}
    """

    msgs = [{'role': 'system', 'content': sys}, {'role': 'user', 'content': user_prompt}]
    result = ai_service.run_text_generation(msgs, config)
    
    if result.get('success'):
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', result['content'].strip(), flags=re.MULTILINE | re.DOTALL)
            return jsonify({'shots': json.loads(cleaned)})
        except: return jsonify({'error': 'Invalid JSON from AI'}), 500
    return jsonify(result), 500

@app.route('/api/generate/image', methods=['POST'])
def generate_image():
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    shot_id = data.get('shot_id')
    pid = data.get('project_id')
    shots_path = os.path.join(get_project_path(pid), 'shot.json')
    shots = read_json(shots_path, default=[])
    current_shot = next((s for s in shots if s['id'] == shot_id), None)
    
    if not current_shot: return jsonify({"error": "Shot not found"}), 404
    
    prev_shot = next((s for s in shots if s['shot_number'] == current_shot['shot_number'] - 1), None)
    
    prev_context = ''
    if prev_shot:  prev_context = prev_shot['end_frame_prompt']
    
    start_prompt_ref = current_shot.get('start_frame_prompt')
    save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
    web_prefix = f"/{IMG_SAVE_DIR}"

    result, used_prompt = ai_service.run_image_generation(
        data.get('visual_description'), data.get('style_description'), data.get('consistency_text'),
        data.get('frame_type'), config, save_dir, web_prefix, start_prompt_ref, prev_context
    )

    if result.get('success'):
        if data.get('frame_type') == 'start': current_shot['start_frame_prompt'] = used_prompt
        else: current_shot['end_frame_prompt'] = used_prompt
        write_json(shots_path, shots)
        return jsonify(result)
    return jsonify(result), 500

@app.route('/api/generate/video', methods=['POST'])
def generate_video():
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    s_url = data.get('start_frame', '')
    e_url = data.get('end_frame', '')
    s_path = os.path.abspath(os.path.join(STATIC_FOLDER, s_url.lstrip('/'))) if s_url else None
    e_path = os.path.abspath(os.path.join(STATIC_FOLDER, e_url.lstrip('/'))) if e_url else None
    
    save_dir = os.path.join(STATIC_FOLDER, VIDEO_SAVE_DIR)
    web_prefix = f"/{VIDEO_SAVE_DIR}"

    result = ai_service.run_video_generation(
        data.get('visual_description'), s_path, e_path, config, save_dir, web_prefix
    )
    return jsonify(result) if result.get('success') else (jsonify(result), 500)

@app.route('/api/generate/voiceover', methods=['POST'])
def generate_voiceover():
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    save_dir = os.path.join(STATIC_FOLDER, AUDIO_SAVE_DIR)
    web_prefix = f"/{AUDIO_SAVE_DIR}"
    
    result = ai_service.run_voice_generation(data.get('text'), config, save_dir, web_prefix)
    return jsonify(result) if result.get('success') else (jsonify(result), 500)

@app.route('/api/projects/<project_id>/export/jianying', methods=['POST'])
def export_jianying(project_id):
    project_info = read_json(os.path.join(get_project_path(project_id), 'info.json'))
    shots = read_json(os.path.join(get_project_path(project_id), 'shot.json'), default=[])
    result = export_draft(project_info, shots, STATIC_FOLDER, EXPORT_DIR)
    return jsonify(result) if result['success'] else (jsonify(result), 500)

@app.route('/api/projects/<project_id>/characters', methods=['GET'])
def get_characters(project_id):
    """获取项目角色列表"""
    characters = read_json(os.path.join(get_project_path(project_id), 'characters.json'), default=[])
    return jsonify(characters)

@app.route('/api/projects/<project_id>/characters', methods=['POST'])
def create_character(project_id):
    """创建新角色"""
    data = request.json
    characters = read_json(os.path.join(get_project_path(project_id), 'characters.json'), default=[])
    character = {
        'id': str(uuid.uuid4()),
        'name': data.get('name'),
        'description': data.get('description'),
        'image_url': '',  # 改为单张图片URL
        'created_time': datetime.now().isoformat()
    }
    characters.append(character)
    write_json(os.path.join(get_project_path(project_id), 'characters.json'), characters)
    return jsonify(character), 201

@app.route('/api/projects/<project_id>/characters/<character_id>', methods=['DELETE'])
def delete_character(project_id, character_id):
    """删除角色"""
    path = os.path.join(get_project_path(project_id), 'characters.json')
    characters = read_json(path, default=[])
    new_characters = [c for c in characters if c['id'] != character_id]
    write_json(path, new_characters)
    return jsonify({"message": "Deleted"})

@app.route('/api/generate/character_views', methods=['POST'])
def generate_character_views():
    """生成角色视图（包含正面特写和多视图的单张图片）"""
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    if data.get('model_name'):
        config['model_name'] = data.get('model_name')

    character_desc = data.get('character_description')
    project_id = data.get('project_id')
    save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
    web_prefix = f"/{IMG_SAVE_DIR}"
    
    # 获取项目信息，包括色彩体系、情感关键词和基础信息
    color_system = None
    emotional_keywords = None
    basic_info = None
    if project_id:
        project_info = read_json(os.path.join(get_project_path(project_id), 'info.json'), default={})
        color_system = project_info.get('visual_color_system', '')
        emotional_keywords = project_info.get('script_emotional_keywords', '')
        basic_info = project_info.get('basic_info', '')

    # 构建包含正面特写和多视图的prompt，并加入色彩体系、情感关键词和基础信息
    prompt = build_comprehensive_character_prompt(character_desc, color_system, emotional_keywords, basic_info)
    
    # 使用不带提示词工程的简单图片生成方法
    result = ai_service.run_simple_image_generation(
        prompt,
        config,
        save_dir,
        web_prefix
    )
    
    if result.get('success'):
        return jsonify({'success': True, 'url': result['url']})
    
    return jsonify({'success': False, 'error': '生成失败'}), 500

def build_comprehensive_character_prompt(character_desc, color_system=None, emotional_keywords=None, basic_info=None):
    """构建包含正面特写和多视图的角色prompt，并加入色彩体系、情感关键词和基础信息"""
    
    # 基础提示词
    prompt = f"""电影角色设计图，{character_desc}。
请生成一张包含以下内容的角色设计图：
1. 左上角：角色正面特写肖像，清晰展示面部特征和表情
2. 右上角：角色正面全身视图，展示完整体型和服装
3. 左下角：角色侧面全身视图，展示体型轮廓和侧面特征
4. 右下角：角色背面全身视图，展示背面服装和轮廓

重要要求：
1. 必须包含四个视图：正面特写肖像、正面全身、侧面全身、背面全身
2. 纯白背景，专业角色设计图风格
3. 清晰的线条和细节
4. 准确的人体比例
5. 精致的服装和配饰细节
6. 无水印，无文字，纯角色展示图
7. 四个视图均匀分布，布局合理，每个视图大小相等
8. 每个视图都有足够的空间展示细节
9. 角色形象必须保持一致，所有视图展示的是同一个角色"""
    
    # 如果有色彩体系，添加到提示词中
    if color_system and color_system.strip():
        prompt += f"""
        
10. 色彩体系要求：{color_system}
11. 角色服装和配饰必须严格遵循指定的色彩体系
12. 整体色调必须与项目的视觉风格保持一致"""
    
    # 如果有情感关键词，添加到提示词中
    if emotional_keywords and emotional_keywords.strip():
        prompt += f"""
        
13. 情感基调：{emotional_keywords}
14. 角色表情和姿态应体现指定的情感基调
15. 整体氛围应与项目的情感风格保持一致"""
    
    # 如果有基础信息，添加到提示词中
    if basic_info and basic_info.strip():
        prompt += f"""
        
16. 项目基础信息：{basic_info}
17. 角色设计应符合项目设定的时代背景、空间环境和人物特点
18. 角色服装、装备和整体风格应与项目世界观保持一致"""
    
    return prompt


@app.route('/api/generate/character_list', methods=['POST'])
def generate_character_list():
    """根据视觉统一设定生成角色列表"""
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    if data.get('model_name'):
        config['model_name'] = data.get('model_name')

    visual_prompt = data.get('visual_consistency_prompt', '')
    if not visual_prompt:
        return jsonify({'success': False, 'error': '视觉统一设定不能为空'}), 400

    sys = "你是一个专业的电影角色设计师。请根据提供的视觉统一设定，生成3-5个主要角色列表，每个角色包含名称和详细描述。"
    msgs = [{'role': 'system', 'content': sys}, 
            {'role': 'user', 'content': f"视觉统一设定：{visual_prompt}\n\n请生成JSON格式的角色列表，格式如下：\n{{\n  \"characters\": [\n    {{\"name\": \"角色名称\", \"description\": \"角色详细描述\"}},\n    ...\n  ]\n}}"}]

    result = ai_service.run_text_generation(msgs, config)
    
    if result.get('success'):
        try:
            # 清理AI返回的文本，提取JSON部分
            content = result.get('content', '')
            # 尝试查找JSON部分
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                character_data = json.loads(json_str)
                return jsonify({'success': True, 'characters': character_data.get('characters', [])})
            else:
                return jsonify({'success': False, 'error': '无法解析角色列表'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': f'解析角色列表失败: {str(e)}'}), 500
    else:
        return jsonify(result), 500


@app.route('/api/upload/character_image', methods=['POST'])
def upload_character_image():
    """上传角色图片"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'}), 400
    
    character_id = request.form.get('character_id')
    # 不再需要view_type，因为只有一张图片
    
    if not character_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    if file and allowed_file(file.filename):
        # 生成唯一文件名
        ext = os.path.splitext(file.filename)[1]
        filename = f"character_{character_id}_{uuid.uuid4().hex[:8]}{ext}"
        
        # 确保目录存在
        save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(save_dir, filename)
        file.save(file_path)
        
        # 返回文件URL
        file_url = f"/{IMG_SAVE_DIR}/{filename}"
        return jsonify({'success': True, 'url': file_url})
    
    return jsonify({'success': False, 'error': '不支持的文件类型'}), 400


def allowed_file(filename):
    """检查文件类型是否允许"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/generate/scene_prompt', methods=['POST'])
def generate_scene_prompt():
    """生成场景提示词"""
    data = request.json
    scene_description = data.get('scene_description')
    project_id = data.get('project_id')
    provider_id = data.get('provider_id')
    model_name = data.get('model_name')

    if not scene_description:
        return jsonify({'success': False, 'error': '场景描述不能为空'}), 400

    # 获取配置
    config = get_provider_config(provider_id)
    if model_name:
        config['model_name'] = model_name

    # 获取项目信息
    project_info = {}
    if project_id:
        project_info = read_json(os.path.join(get_project_path(project_id), 'info.json'), default={})

    # 构建系统提示词
    sys = "你是一个专业的电影场景设计师。请根据场景描述生成详细的场景提示词，用于AI图片生成。"
    
    # 构建用户提示词，包含场景描述和项目信息
    user_prompt = f"""场景描述：{scene_description}

请生成一个详细的场景提示词，必须包含以下元素：
1. 精确的时间设定（早晨、中午、下午、傍晚、夜晚等）
2. 天气状况（晴朗、阴天、雨天、雪天等）
3. 光源类型和方向（自然光、人造光、逆光等）
4. 空间类型（室内、室外、半开放空间等）
5. 空间尺度（狭小、适中、广阔等）
6. 场景高度（低角度、平视、高角度等）
7. 场景中的标志性建筑或物体
8. 背景、前景和氛围的详细框架说明
9. 整体氛围（宁静、紧张、欢乐等）
10. 整体风格（写实、卡通、奇幻等）
11. 景别（远景、全景、中景、近景等）
12. 视角设定（平视、俯视、仰视等）
13. 构图方式（对称、黄金分割、对角线等）

请直接返回提示词内容，不要包含其他解释或说明。"""

    # 如果有项目信息，添加到提示词中
    if project_info:
        color_system = project_info.get('visual_color_system', '')
        emotional_keywords = project_info.get('script_emotional_keywords', '')
        basic_info = project_info.get('basic_info', '')
        
        if color_system:
            user_prompt += f"\n\n色彩体系要求：{color_system}"
        if emotional_keywords:
            user_prompt += f"\n\n情感基调：{emotional_keywords}"
        if basic_info:
            user_prompt += f"\n\n项目基础信息：{basic_info}"

    msgs = [{'role': 'system', 'content': sys}, {'role': 'user', 'content': user_prompt}]

    result = ai_service.run_text_generation(msgs, config)

    if result.get('success'):
        return jsonify({'success': True, 'prompt': result['content']})
    else:
        return jsonify({'success': False, 'error': result.get('error', '生成失败')}), 500


@app.route('/api/generate/scene_image', methods=['POST'])
def generate_scene_image():
    """生成场景图片"""
    data = request.json
    scene_id = data.get('scene_id')
    scene_prompt = data.get('scene_prompt')
    provider_id = data.get('provider_id')
    model_name = data.get('model_name')
    
    if not scene_prompt:
        return jsonify({'success': False, 'error': '场景提示词不能为空'}), 400
    
    # 构建场景图片生成的提示词
    full_prompt = f"""电影场景设计图，{scene_prompt}。
    请生成一张高质量的场景设计图，包含以下元素：
    1. 精确的时间设定（早晨、中午、下午、傍晚、夜晚等）
    2. 天气状况（晴朗、阴天、雨天、雪天等）
    3. 光源类型和方向（自然光、人造光、逆光等）
    4. 空间类型（室内、室外、半开放空间等）
    5. 空间尺度（狭小、适中、广阔等）
    6. 场景高度（低角度、平视、高角度等）
    7. 场景中的标志性建筑或物体
    8. 背景、前景和氛围的详细框架说明
    9. 整体氛围（宁静、紧张、欢乐等）
    10. 整体风格（写实、卡通、奇幻等）
    11. 景别（远景、全景、中景、近景等）
    12. 视角设定（平视、俯视、仰视等）
    13. 构图方式（对称、黄金分割、对角线等）
    
    图片要求：
    - 高分辨率，细节丰富
    - 电影级质感，色彩协调
    - 光影效果真实自然
    - 构图均衡，有深度感"""
    
    # 获取配置
    config = get_provider_config(provider_id)
    if model_name:
        config['model_name'] = model_name
    
    # 设置保存路径
    save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
    web_prefix = f"/{IMG_SAVE_DIR}"
    
    # 使用AI服务生成图片
    result = ai_service.run_simple_image_generation(
        full_prompt,
        config,
        save_dir,
        web_prefix
    )
    
    if result.get('success'):
        return jsonify({'success': True, 'url': result['url']})
    else:
        return jsonify({'success': False, 'error': result.get('error_msg', '生成失败')}), 500

@app.route('/api/projects/<project_id>/characters/<character_id>', methods=['PUT'])
def update_character(project_id, character_id):
    """更新角色信息"""
    data = request.json
    path = os.path.join(get_project_path(project_id), 'characters.json')
    characters = read_json(path, default=[])
    
    for i, char in enumerate(characters):
        if char['id'] == character_id:
            # 更新角色信息
            updated_char = {**char, **data}
            characters[i] = updated_char
            write_json(path, characters)
            return jsonify(updated_char)
    
    return jsonify({"error": "Not found"}), 404


if __name__ == '__main__':
    ensure_dirs()
    print(f"Server started on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)