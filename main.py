import os
import json
import uuid
import time
import re
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

# --- 工具函数 ---
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
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
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
    character_biography: str = ""
    worldview_background: str = ""
    worldview_spatial_trait: str = ""
    director_emotional_intensity: int = 5
    director_expression_focus: str = ""
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

# --- Settings CRUD ---
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

# --- Project CRUD ---
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

# --- Script/Shot CRUD ---
@app.route('/api/projects/<project_id>/script', methods=['GET'])
def get_script(project_id): return jsonify(read_json(os.path.join(get_project_path(project_id), 'script.json'), default=[]))

@app.route('/api/projects/<project_id>/script', methods=['POST'])
def save_script(project_id):
    write_json(os.path.join(get_project_path(project_id), 'script.json'), request.json)
    return jsonify({"success": True})

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

# --- AI & Export ---
@app.route('/api/generate/script_continuation', methods=['POST'])
def generate_script_continuation():
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    sys = "你是一个专业的中文电影编剧助手。"
    msgs = [{'role': 'system', 'content': sys}, {'role': 'user', 'content': f"前文：\n{data.get('context_text','')}\n\n请续写："}]
    result = ai_service.run_text_generation(msgs, config)
    return jsonify(result) if result.get('success') else (jsonify(result), 500)

@app.route('/api/generate/analyze_script', methods=['POST'])
def analyze_script():
    data = request.json
    config = get_provider_config(data.get('provider_id'))
    result = ai_service.run_script_analysis(data.get('content', ''), config)
    if result.get('success'):
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', result['content'].strip(), flags=re.MULTILINE | re.DOTALL)
            return jsonify({'shots': json.loads(cleaned)})
        except: return jsonify({'error': 'Invalid JSON'}), 500
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
    
    start_prompt_ref = current_shot.get('start_frame_prompt') if current_shot else ""
    prev_context = "" 
    
    save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
    web_prefix = f"/{IMG_SAVE_DIR}"

    result, used_prompt = ai_service.run_image_generation(
        data.get('visual_description'), data.get('style_description'), data.get('consistency_text'),
        data.get('frame_type'), config, save_dir, web_prefix, start_prompt_ref, prev_context
    )
    
    if result.get('success') and current_shot:
        if data.get('frame_type') == 'start': current_shot['start_frame_prompt'] = used_prompt
        else: current_shot['end_frame_prompt'] = used_prompt
        write_json(shots_path, shots)
        return jsonify(result)
    return jsonify(result), 500 if not result.get('success') else 200

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

    result = ai_service.run_video_generation(data.get('visual_description'), s_path, e_path, config, save_dir, web_prefix)
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

if __name__ == '__main__':
    ensure_dirs()
    print(f"Server started on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)