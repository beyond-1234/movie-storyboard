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

# 引入 AI 服务
from ai_service import generate_aliyun_image, generate_aliyun_video, generate_aliyun_text, generate_aliyun_voiceover
# 引入 剪映导出服务 (新)
from jianying_exporter import export_draft

# --- 配置 ---
DATA_DIR = "projects"
STATIC_FOLDER = "."
IMG_SAVE_DIR = "static/imgs"
VIDEO_SAVE_DIR = "static/videos"
AUDIO_SAVE_DIR = "static/audio"
SETTINGS_FILE = "settings.json"
# 导出目录
EXPORT_DIR = "exports"

app = Flask(__name__, static_url_path='', static_folder=STATIC_FOLDER)

# --- 工具函数 ---
def ensure_dirs():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    Path(IMG_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    Path(VIDEO_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    Path(AUDIO_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    Path(EXPORT_DIR).mkdir(parents=True, exist_ok=True)

def get_project_path(project_id): return os.path.join(DATA_DIR, project_id)

def read_json(filepath, default=None):
    if not os.path.exists(filepath): return default if default is not None else {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception as e: print(f"Error reading {filepath}: {e}"); return default if default is not None else {}

def write_json(filepath, data):
    directory = os.path.dirname(filepath)
    if directory: os.makedirs(directory, exist_ok=True)
    def json_serial(obj):
        if isinstance(obj, datetime): return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, default=json_serial, indent=4, ensure_ascii=False)

def get_settings_data(): return read_json(SETTINGS_FILE, default={'providers': []})

def get_provider_config(provider_id):
    settings = get_settings_data()
    for p in settings.get('providers', []):
        if p.get('id') == provider_id: return p
    return None

def get_aliyun_api_key(provider_id=None):
    if provider_id:
        conf = get_provider_config(provider_id)
        if conf: return conf.get('api_key')
    settings = get_settings_data()
    for p in settings.get('providers', []):
        if p.get('type') == 'aliyun' and p.get('enabled'): return p.get('api_key')
    return None

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
    def from_dict(cls, data: Dict[str, Any]):
        valid_keys = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
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
    def from_dict(cls, data: Dict[str, Any]):
        valid_keys = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
    def to_dict(self): return asdict(self)

# --- 路由 ---
@app.route('/')
def index(): return send_file('index.html')

# ... [Settings APIs omitted] ...
@app.route('/api/settings', methods=['GET'])
def get_settings():
    data = get_settings_data()
    providers = data.get('providers', [])
    response_list = []
    for p in providers:
        p_copy = p.copy()
        if p_copy.get('api_key'): p_copy['api_key'] = p_copy['api_key'][:6] + '******'
        if 'models' not in p_copy: p_copy['models'] = []
        for m in p_copy['models']:
            if 'type' not in m: m['type'] = 'image' 
        response_list.append(p_copy)
    return jsonify(response_list)

@app.route('/api/settings/provider', methods=['POST'])
def save_provider():
    req_data = request.json
    settings = get_settings_data()
    if 'providers' not in settings: settings['providers'] = []
    p_id = req_data.get('id')
    new_provider = {
        'id': p_id or str(uuid.uuid4()), 'name': req_data.get('name', 'New Provider'), 'type': req_data.get('type', 'aliyun'),
        'base_url': req_data.get('base_url', ''), 'models': req_data.get('models', []), 'enabled': req_data.get('enabled', True)
    }
    input_key = req_data.get('api_key', '')
    if p_id:
        found = False
        for i, p in enumerate(settings['providers']):
            if p['id'] == p_id:
                if '******' in input_key: new_provider['api_key'] = p.get('api_key', '')
                else: new_provider['api_key'] = input_key
                settings['providers'][i] = new_provider; found = True; break
        if not found: new_provider['api_key'] = input_key; settings['providers'].append(new_provider)
    else:
        new_provider['api_key'] = input_key; settings['providers'].append(new_provider)
    write_json(SETTINGS_FILE, settings)
    return jsonify({"success": True, "id": new_provider['id']})

@app.route('/api/settings/provider/<provider_id>', methods=['DELETE'])
def delete_provider(provider_id):
    settings = get_settings_data()
    original_len = len(settings.get('providers', []))
    settings['providers'] = [p for p in settings.get('providers', []) if p['id'] != provider_id]
    if len(settings['providers']) < original_len: write_json(SETTINGS_FILE, settings); return jsonify({"success": True})
    return jsonify({"error": "Provider not found"}), 404

# ... [Project APIs omitted] ...
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

# ... [Script APIs omitted] ...
@app.route('/api/projects/<project_id>/script', methods=['GET'])
def get_script(project_id): return jsonify(read_json(os.path.join(get_project_path(project_id), 'script.json'), default=[]))

@app.route('/api/projects/<project_id>/script', methods=['POST'])
def save_script(project_id):
    write_json(os.path.join(get_project_path(project_id), 'script.json'), request.json)
    return jsonify({"success": True})

# ... [AI Text/Analyze APIs omitted] ...
@app.route('/api/generate/script_continuation', methods=['POST'])
def generate_script_continuation():
    data = request.json
    provider_id = data.get('provider_id')
    system_prompt = "你是一个专业的中文电影编剧助手。请根据前文续写一段剧本。要求：全中文，画面感强。"
    messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': f"前文：\n{data.get('context_text','')}\n\n请续写："}]
    api_key = get_aliyun_api_key(provider_id)
    result = generate_aliyun_text(messages, api_key=api_key, model='qwen-plus')
    return jsonify({'content': result['content']}) if result['success'] else (jsonify({'error': result.get('error_msg')}), 500)

@app.route('/api/generate/analyze_script', methods=['POST'])
def analyze_script():
    data = request.json
    script_content = data.get('content', '')
    provider_id = data.get('provider_id')
    model = data.get('model', 'qwen-plus')
    if not script_content: return jsonify({'error': 'Empty content'}), 400
    system_prompt = """作为专业的电影分镜师，请分析以下剧本片段，将其转化为分镜表数据。
    **输出要求**：1. 返回一个纯 JSON 数组。2. **必须使用中文**填写所有描述性字段。3. 不要包含 Markdown 标记。
    **JSON对象结构**：- scene: 场次 - shot_number: 镜号 - visual_description: 画面说明 - audio_description: 声音说明 - dialogue: 台词 - duration: 时长 - special_technique: 特殊技术"""
    messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': f"剧本片段：\n{script_content}"}]
    api_key = get_aliyun_api_key(provider_id)
    result = generate_aliyun_text(messages, api_key=api_key, model=model)
    if result['success']:
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', result['content'].strip(), flags=re.MULTILINE | re.DOTALL)
            return jsonify({'shots': json.loads(cleaned)})
        except: return jsonify({'error': 'Invalid JSON'}), 500
    return jsonify({'error': result.get('error_msg')}), 500

# ... [Shot APIs omitted] ...
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

# ... [Generate APIs omitted for brevity, keep as is] ...
def generate_optimized_prompt(api_key, frame_type, visual_desc, style_desc, consistency_text="", start_prompt_ref=None, prev_shot_context=""):
    consistency_instruction = f"**GLOBAL VISUAL RULES**: {consistency_text}. Maintain consistent characters and environment.\n" if consistency_text else ""
    context_instruction = f"\n**PREVIOUS SHOT CONTEXT**: \"{prev_shot_context}\". Ensure narrative continuity." if prev_shot_context else ""
    if frame_type == 'start':
        sys_prompt = f"""You are an expert AI Art Prompt Engineer. Convert user's description into a high-quality English prompt. {consistency_instruction}{context_instruction} Requirements: 1. Describe subject, environment, lighting, composition, style. 2. Use English, comma-separated. 3. Emphasize cinematic quality. 4. DIRECTLY output prompt text only."""
        user_prompt = f"Style: {style_desc}\nDescription: {visual_desc}"
    else:
        sys_prompt = f"""You are an expert AI Art Prompt Engineer. Generate an [End Frame] prompt based on the [Start Frame Prompt]. {consistency_instruction} Requirements: 1. **KEEP** character appearance, background, and style from Start Frame Prompt EXACTLY the same. 2. **ONLY CHANGE** action/pose based on 'End Frame Description'. 3. Use English. 4. DIRECTLY output prompt text only."""
        user_prompt = f"Start Frame Prompt: {start_prompt_ref}\n\nEnd Frame Action: {visual_desc}"
    messages = [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}]
    result = generate_aliyun_text(messages, api_key=api_key, model='qwen-plus')
    if result['success']: return result['content']
    else: return f"Cinematic shot, {style_desc}, {visual_desc}"

@app.route('/api/generate/image', methods=['POST'])
def generate_image():
    data = request.json
    provider_id = data.get('provider_id') 
    model_name = data.get('model_name', 'qwen-image-plus') 
    visual_desc = data.get('visual_description', '')
    style_desc = data.get('style_description', '') 
    consistency_text = data.get('consistency_text', '')
    frame_type = data.get('frame_type', 'start')
    shot_id = data.get('shot_id')
    project_id = data.get('project_id')

    if not visual_desc: return jsonify({"error": "Missing visual description"}), 400
    config = get_provider_config(provider_id)
    if not config or config.get('type') == 'mock':
        time.sleep(1.0)
        return jsonify({"url": f"https://placehold.co/600x400/2c3e50/ffffff?text={frame_type}+Mock"})

    api_key = config.get('api_key')
    final_prompt = ""
    shots_path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(shots_path, default=[])
    target_shot_index = -1
    current_shot = None
    for i, s in enumerate(shots):
        if s['id'] == shot_id: target_shot_index = i; current_shot = s; break
    if not current_shot: return jsonify({"error": "Shot not found"}), 404
    prev_shot_context = ""
    if target_shot_index > 0: prev_shot_context = shots[target_shot_index - 1].get('visual_description', '')
    if frame_type == 'start':
        final_prompt = generate_optimized_prompt(api_key, 'start', visual_desc, style_desc, consistency_text, prev_shot_context=prev_shot_context)
        current_shot['start_frame_prompt'] = final_prompt
    else:
        start_prompt = current_shot.get('start_frame_prompt', '')
        if not start_prompt:
            start_prompt = generate_optimized_prompt(api_key, 'start', visual_desc, style_desc, consistency_text)
            current_shot['start_frame_prompt'] = start_prompt
        final_prompt = generate_optimized_prompt(api_key, 'end', visual_desc, style_desc, consistency_text, start_prompt_ref=start_prompt)
        current_shot['end_frame_prompt'] = final_prompt
    shots[target_shot_index] = current_shot
    write_json(shots_path, shots)
    provider_type = config.get('type')
    base_url = config.get('base_url', '')
    models = config.get('models', [])
    model_config = next((m for m in models if m['name'] == model_name), None)
    full_endpoint = base_url
    if model_config and model_config.get('path'): full_endpoint = base_url.rstrip('/') + '/' + model_config.get('path').lstrip('/')
    elif base_url: full_endpoint = base_url
    if provider_type == 'aliyun':
        save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
        web_prefix = f"/{IMG_SAVE_DIR}"
        result = generate_aliyun_image(final_prompt, save_dir, web_prefix, api_key=api_key, model=model_name, endpoint=full_endpoint)
        if result['success']: return jsonify({"url": result['url']})
        else: return jsonify({"error": result['error_msg']}), result['status_code']
    return jsonify({"error": "Unsupported provider type"}), 400

@app.route('/api/generate/video', methods=['POST'])
def generate_video():
    data = request.json
    provider_id = data.get('provider_id')
    model_name = data.get('model_name', 'wanx2.1-kf2v-plus')
    visual_desc = data.get('visual_description', '')
    start_frame_url = data.get('start_frame', '')
    end_frame_url = data.get('end_frame', '')
    prompt = f"Cinematic shot, {visual_desc}, high quality, smooth motion."
    config = get_provider_config(provider_id)
    if not config or config.get('type') == 'mock':
        time.sleep(2)
        return jsonify({"url": "https://www.w3schools.com/html/mov_bbb.mp4"})
    api_key = config.get('api_key')
    provider_type = config.get('type')
    base_url = config.get('base_url', '')
    models = config.get('models', [])
    model_config = next((m for m in models if m['name'] == model_name), None)
    full_endpoint = base_url
    if model_config and model_config.get('path'): full_endpoint = base_url.rstrip('/') + '/' + model_config.get('path').lstrip('/')
    elif base_url: full_endpoint = base_url
    if provider_type == 'aliyun':
        real_start_path = None
        real_end_path = None
        if start_frame_url.startswith('/static/') or start_frame_url.startswith('static/'):
            real_start_path = os.path.abspath(os.path.join(STATIC_FOLDER, start_frame_url.lstrip('/')))
        if end_frame_url.startswith('/static/') or end_frame_url.startswith('static/'):
            real_end_path = os.path.abspath(os.path.join(STATIC_FOLDER, end_frame_url.lstrip('/')))
        save_dir = os.path.join(STATIC_FOLDER, VIDEO_SAVE_DIR)
        web_prefix = f"/{VIDEO_SAVE_DIR}"
        result = generate_aliyun_video(prompt, save_dir, web_prefix, api_key=api_key, model=model_name, endpoint=full_endpoint, start_img_path=real_start_path, end_img_path=real_end_path)
        if result['success']: return jsonify({"url": result['url']})
        else: return jsonify({"error": result['error_msg']}), result['status_code']
    return jsonify({"error": "Unsupported provider type"}), 400

@app.route('/api/generate/voiceover', methods=['POST'])
def generate_voiceover():
    data = request.json
    provider_id = data.get('provider_id')
    text = data.get('text', '')
    voice = data.get('voice', 'Cherry')
    model_name = data.get('model_name', 'qwen3-tts-flash') 
    if not text: return jsonify({"error": "Missing text"}), 400
    config = get_provider_config(provider_id)
    if not config or config.get('type') == 'mock':
        time.sleep(1.0)
        return jsonify({"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"})
    api_key = config.get('api_key')
    provider_type = config.get('type')
    if provider_type == 'aliyun':
        save_dir = os.path.join(STATIC_FOLDER, AUDIO_SAVE_DIR)
        web_prefix = f"/{AUDIO_SAVE_DIR}"
        base_url = config.get('base_url', '')
        result = generate_aliyun_voiceover(text, save_dir, web_prefix, api_key=api_key, voice=voice, endpoint=base_url, model=model_name)
        if result['success']: return jsonify({"url": result['url']})
        else: return jsonify({"error": result['error_msg']}), result.get('status_code', 500)
    return jsonify({"error": "Unsupported provider type"}), 400

# --- 剪映导出接口 ---

@app.route('/api/projects/<project_id>/export/jianying', methods=['POST'])
def export_jianying(project_id):
    project_info = read_json(os.path.join(get_project_path(project_id), 'info.json'))
    shots = read_json(os.path.join(get_project_path(project_id), 'shot.json'), default=[])
    
    result = export_draft(project_info, shots, STATIC_FOLDER, EXPORT_DIR)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify({"error": result['error']}), 500

if __name__ == '__main__':
    ensure_dirs()
    print(f"Server started on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)