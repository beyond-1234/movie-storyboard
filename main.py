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

# 引入拆分后的 AI 服务 (同步版本)
from ai_service import generate_aliyun_image, generate_aliyun_video, generate_aliyun_text

# --- 配置 ---
DATA_DIR = "projects"
STATIC_FOLDER = "."  # 当前目录作为静态文件目录
IMG_SAVE_DIR = "static/imgs" # 图片保存子目录（相对于 STATIC_FOLDER）
VIDEO_SAVE_DIR = "static/videos" # 视频保存子目录
SETTINGS_FILE = "settings.json" # 全局配置文件

app = Flask(__name__, static_url_path='', static_folder=STATIC_FOLDER)

# --- 工具函数 ---

def ensure_dirs():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    Path(IMG_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    Path(VIDEO_SAVE_DIR).mkdir(parents=True, exist_ok=True)

def get_project_path(project_id):
    return os.path.join(DATA_DIR, project_id)

def read_json(filepath, default=None):
    if not os.path.exists(filepath):
        return default if default is not None else {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return default if default is not None else {}

def write_json(filepath, data):
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    def json_serial(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, default=json_serial, indent=4, ensure_ascii=False)

def get_settings_data():
    return read_json(SETTINGS_FILE, default={'providers': []})

def get_provider_config(provider_id):
    """根据ID获取供应商配置"""
    settings = get_settings_data()
    for p in settings.get('providers', []):
        if p.get('id') == provider_id:
            return p
    return None

def get_aliyun_api_key(provider_id=None):
    """辅助函数：获取 Aliyun API Key"""
    if provider_id:
        conf = get_provider_config(provider_id)
        if conf: return conf.get('api_key')

    # 否则找第一个开启的 aliyun provider
    settings = get_settings_data()
    for p in settings.get('providers', []):
        if p.get('type') == 'aliyun' and p.get('enabled'):
            return p.get('api_key')
    return None

# --- 数据模型 (Data Classes) ---

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
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_time: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_time: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        valid_keys = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)

    def to_dict(self):
        return asdict(self)

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
    video_url: str = "" # 新增：视频链接
    images: List[str] = field(default_factory=list)

    created_time: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_time: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        valid_keys = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)

    def to_dict(self):
        return asdict(self)

# --- 路由 (Routes) ---

@app.route('/')
def index():
    return send_file('index.html')

# --- 系统设置接口 (CRUD) ---

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取所有供应商配置列表"""
    data = get_settings_data()
    providers = data.get('providers', [])

    response_list = []
    for p in providers:
        p_copy = p.copy()
        if p_copy.get('api_key'):
            p_copy['api_key'] = p_copy['api_key'][:6] + '******'

        if 'models' not in p_copy:
            p_copy['models'] = []

        for m in p_copy['models']:
            if 'type' not in m:
                m['type'] = 'image'

        response_list.append(p_copy)

    return jsonify(response_list)

@app.route('/api/settings/provider', methods=['POST'])
def save_provider():
    req_data = request.json
    settings = get_settings_data()
    if 'providers' not in settings:
        settings['providers'] = []

    p_id = req_data.get('id')

    new_provider = {
        'id': p_id or str(uuid.uuid4()),
        'name': req_data.get('name', 'New Provider'),
        'type': req_data.get('type', 'aliyun'),
        'base_url': req_data.get('base_url', ''),
        'models': req_data.get('models', []),
        'enabled': req_data.get('enabled', True)
    }

    input_key = req_data.get('api_key', '')

    if p_id:
        found = False
        for i, p in enumerate(settings['providers']):
            if p['id'] == p_id:
                if '******' in input_key:
                    new_provider['api_key'] = p.get('api_key', '')
                else:
                    new_provider['api_key'] = input_key

                settings['providers'][i] = new_provider
                found = True
                break
        if not found:
            new_provider['api_key'] = input_key
            settings['providers'].append(new_provider)
    else:
        new_provider['api_key'] = input_key
        settings['providers'].append(new_provider)

    write_json(SETTINGS_FILE, settings)
    return jsonify({"success": True, "id": new_provider['id']})

@app.route('/api/settings/provider/<provider_id>', methods=['DELETE'])
def delete_provider(provider_id):
    settings = get_settings_data()
    original_len = len(settings.get('providers', []))
    settings['providers'] = [p for p in settings.get('providers', []) if p['id'] != provider_id]

    if len(settings['providers']) < original_len:
        write_json(SETTINGS_FILE, settings)
        return jsonify({"success": True})
    return jsonify({"error": "Provider not found"}), 404

# --- 项目管理接口 ---

@app.route('/api/projects', methods=['GET'])
def get_projects():
    ensure_dirs()
    projects = []
    if os.path.exists(DATA_DIR):
        for pid in os.listdir(DATA_DIR):
            info_path = os.path.join(DATA_DIR, pid, 'info.json')
            if os.path.exists(info_path):
                data = read_json(info_path)
                projects.append(data)
    projects.sort(key=lambda x: x.get('updated_time', ''), reverse=True)
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    if not data.get('film_name'):
        return jsonify({"error": "项目名称必填"}), 400

    project = MovieProject.from_dict(data)
    path = os.path.join(get_project_path(project.id), 'info.json')
    write_json(path, project.to_dict())

    shot_path = os.path.join(get_project_path(project.id), 'shot.json')
    write_json(shot_path, [])

    # 初始化脚本文件
    script_path = os.path.join(get_project_path(project.id), 'script.json')
    write_json(script_path, [])

    return jsonify(project.to_dict()), 201

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    path = os.path.join(get_project_path(project_id), 'info.json')
    data = read_json(path)
    if not data:
        return jsonify({"error": "项目不存在"}), 404
    return jsonify(data)

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    path = os.path.join(get_project_path(project_id), 'info.json')
    data = read_json(path)
    if not data:
        return jsonify({"error": "项目不存在"}), 404

    update_data = request.json
    update_data['id'] = project_id
    update_data['created_time'] = data.get('created_time')
    update_data['updated_time'] = datetime.now().isoformat()

    new_project = MovieProject.from_dict({**data, **update_data})
    write_json(path, new_project.to_dict())
    return jsonify(new_project.to_dict())

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    import shutil
    path = get_project_path(project_id)
    if os.path.exists(path):
        shutil.rmtree(path)
        return jsonify({"message": "删除成功"})
    return jsonify({"error": "项目不存在"}), 404

# --- 剧本管理接口 ---

@app.route('/api/projects/<project_id>/script', methods=['GET'])
def get_script(project_id):
    path = os.path.join(get_project_path(project_id), 'script.json')
    script_data = read_json(path, default=[])
    return jsonify(script_data)

@app.route('/api/projects/<project_id>/script', methods=['POST'])
def save_script(project_id):
    data = request.json
    path = os.path.join(get_project_path(project_id), 'script.json')
    write_json(path, data)

    # 更新项目时间
    p_path = os.path.join(get_project_path(project_id), 'info.json')
    p_data = read_json(p_path)
    if p_data:
        p_data['updated_time'] = datetime.now().isoformat()
        write_json(p_path, p_data)

    return jsonify({"success": True})

# --- AI 文本与分镜分析接口 ---

@app.route('/api/generate/text', methods=['POST'])
def generate_text_api():
    """通用 AI 文本生成（用于剧本续写）"""
    data = request.json
    messages = data.get('messages', [])
    model = data.get('model', 'qwen-plus')
    provider_id = data.get('provider_id')

    api_key = get_aliyun_api_key(provider_id)

    result = generate_aliyun_text(messages, api_key=api_key, model=model)

    if result['success']:
        return jsonify({'content': result['content']})
    else:
        return jsonify({'error': result.get('error_msg', 'Unknown Error')}), result.get('status_code', 500)

@app.route('/api/generate/analyze_script', methods=['POST'])
def analyze_script():
    """将剧本段落转化为分镜 JSON 数据"""
    data = request.json
    script_content = data.get('content', '')
    provider_id = data.get('provider_id')
    model = data.get('model', 'qwen-plus')

    if not script_content:
        return jsonify({'error': 'Empty content'}), 400

    system_prompt = """
    作为专业的电影分镜师，请分析以下剧本片段，将其转化为分镜表数据。
    请返回一个JSON数组，数组中每个对象包含以下字段：
    - scene: 场次 (例如 "1", "EXT. PARK")
    - shot_number: 镜号 (例如 "1", "1A")
    - visual_description: 画面说明 (详细描述画面内容，用于AI生图)
    - audio_description: 声音说明 (对白、音效)
    - duration: 时长 (例如 "3s")
    - special_technique: 特殊技术 (例如 "推拉", "特写")

    请只返回JSON字符串，不要包含markdown标记（如```json ... ```）。
    """

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f"剧本片段：\n{script_content}"}
    ]

    api_key = get_aliyun_api_key(provider_id)
    result = generate_aliyun_text(messages, api_key=api_key, model=model)

    if result['success']:
        raw_content = result['content']
        # 清理可能的 markdown 标记
        cleaned_content = re.sub(r'^```json\s*|\s*```$', '', raw_content.strip(), flags=re.MULTILINE | re.DOTALL)
        try:
            shots_data = json.loads(cleaned_content)
            return jsonify({'shots': shots_data})
        except json.JSONDecodeError:
            return jsonify({'error': 'AI returned invalid JSON', 'raw': raw_content}), 500
    else:
        return jsonify({'error': result.get('error_msg')}), result.get('status_code', 500)


# --- 分镜管理接口 ---

@app.route('/api/projects/<project_id>/shots', methods=['GET'])
def get_shots(project_id):
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])

    def sort_key(s):
        try:
            return (s.get('scene', ''), float(s.get('shot_number', 0)))
        except:
            return (s.get('scene', ''), s.get('shot_number', ''))

    shots.sort(key=sort_key)
    return jsonify(shots)

@app.route('/api/projects/<project_id>/shots', methods=['POST'])
def create_shot(project_id):
    data = request.json
    data['movie_id'] = project_id
    if not data.get('shot_number'):
        return jsonify({"error": "镜头号必填"}), 400

    new_shot = StoryboardShot.from_dict(data)
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])
    shots.append(new_shot.to_dict())
    write_json(path, shots)

    p_path = os.path.join(get_project_path(project_id), 'info.json')
    p_data = read_json(p_path)
    if p_data:
        p_data['updated_time'] = datetime.now().isoformat()
        write_json(p_path, p_data)

    return jsonify(new_shot.to_dict()), 201

@app.route('/api/projects/<project_id>/shots/<shot_id>', methods=['PUT'])
def update_shot(project_id, shot_id):
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])

    found_index = -1
    for i, shot in enumerate(shots):
        if shot['id'] == shot_id:
            found_index = i
            break

    if found_index == -1:
        return jsonify({"error": "分镜不存在"}), 404

    update_data = request.json
    current_data = shots[found_index]

    update_data['id'] = shot_id
    update_data['movie_id'] = project_id
    update_data['created_time'] = current_data.get('created_time')
    update_data['updated_time'] = datetime.now().isoformat()

    updated_shot = StoryboardShot.from_dict({**current_data, **update_data})
    shots[found_index] = updated_shot.to_dict()

    write_json(path, shots)
    return jsonify(updated_shot.to_dict())

@app.route('/api/projects/<project_id>/shots/<shot_id>', methods=['DELETE'])
def delete_shot(project_id, shot_id):
    path = os.path.join(get_project_path(project_id), 'shot.json')
    shots = read_json(path, default=[])
    new_shots = [s for s in shots if s['id'] != shot_id]
    if len(new_shots) == len(shots):
        return jsonify({"error": "分镜不存在"}), 404
    write_json(path, new_shots)
    return jsonify({"message": "删除成功"})

# --- 媒体生成接口 ---

@app.route('/api/generate/image', methods=['POST'])
def generate_image():
    """图片生成入口"""
    data = request.json
    provider_id = data.get('provider_id')
    model_name = data.get('model_name', 'qwen-image-plus')
    prompt = data.get('prompt', '')
    frame_type = data.get('frame_type', 'start') # start or end

    # 自动修改 Prompt
    if frame_type == 'end':
        prompt = f"{prompt}, end frame of the shot, showing the result of the action, consistent style"
    else:
        prompt = f"{prompt}, start frame of the shot, cinematic composition"

    # 获取配置
    config = get_provider_config(provider_id)

    # 兼容 Mock 模式
    if not config or config.get('type') == 'mock':
        time.sleep(1.0)
        safe_prompt = prompt[:20].replace(" ", "+") if prompt else "Scene"
        label = "EndFrame" if frame_type == 'end' else "StartFrame"
        mock_url = f"https://placehold.co/600x400/2c3e50/ffffff?text={label}:+{safe_prompt}\\n(Mock)"
        return jsonify({"url": mock_url})

    api_key = config.get('api_key')
    provider_type = config.get('type')

    # 构造拼接后的 Base URL
    base_url = config.get('base_url', '')
    models = config.get('models', [])
    model_config = next((m for m in models if m['name'] == model_name), None)

    full_endpoint = base_url
    if model_config and model_config.get('path'):
        path = model_config.get('path')
        if base_url.endswith('/') and path.startswith('/'):
            full_endpoint = base_url + path[1:]
        elif not base_url.endswith('/') and not path.startswith('/'):
            full_endpoint = base_url + '/' + path
        else:
            full_endpoint = base_url + path

    # 调用 Aliyun
    if provider_type == 'aliyun':
        save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
        web_prefix = f"/{IMG_SAVE_DIR}"

        result = generate_aliyun_image(prompt, save_dir, web_prefix, api_key=api_key, model=model_name, endpoint=full_endpoint)

        if result['success']:
            return jsonify({"url": result['url']})
        else:
            return jsonify({"error": result['error_msg']}), result['status_code']

    return jsonify({"error": "Unsupported provider type"}), 400

@app.route('/api/generate/video', methods=['POST'])
def generate_video():
    """视频生成入口 (同步调用)"""
    data = request.json
    provider_id = data.get('provider_id')
    model_name = data.get('model_name', 'wanx2.1-kf2v-plus')
    prompt = data.get('prompt', '')
    start_frame_url = data.get('start_frame', '')
    end_frame_url = data.get('end_frame', '')

    config = get_provider_config(provider_id)

    if not config or config.get('type') == 'mock':
        time.sleep(2)
        mock_video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
        return jsonify({"url": mock_video_url})

    api_key = config.get('api_key')
    provider_type = config.get('type')

    # Base URL 构造逻辑
    base_url = config.get('base_url', '')
    models = config.get('models', [])
    model_config = next((m for m in models if m['name'] == model_name), None)

    full_endpoint = base_url
    if model_config and model_config.get('path'):
        path = model_config.get('path')
        if base_url.endswith('/') and path.startswith('/'):
            full_endpoint = base_url + path[1:]
        elif not base_url.endswith('/') and not path.startswith('/'):
            full_endpoint = base_url + '/' + path
        else:
            full_endpoint = base_url + path

    if provider_type == 'aliyun':
        # 解析本地文件路径
        real_start_path = None
        real_end_path = None

        if start_frame_url and (start_frame_url.startswith('/static/') or start_frame_url.startswith('static/')):
            clean = start_frame_url.lstrip('/')
            real_start_path = os.path.abspath(os.path.join(STATIC_FOLDER, clean))

        if end_frame_url and (end_frame_url.startswith('/static/') or end_frame_url.startswith('static/')):
            clean = end_frame_url.lstrip('/')
            real_end_path = os.path.abspath(os.path.join(STATIC_FOLDER, clean))

        # 准备保存路径
        save_dir = os.path.join(STATIC_FOLDER, VIDEO_SAVE_DIR)
        web_prefix = f"/{VIDEO_SAVE_DIR}"

        # 同步调用
        result = generate_aliyun_video(
            prompt,
            save_dir,
            web_prefix,
            api_key=api_key,
            model=model_name,
            endpoint=full_endpoint,
            start_img_path=real_start_path,
            end_img_path=real_end_path
        )

        if result['success']:
            return jsonify({"url": result['url']})
        else:
            return jsonify({"error": result['error_msg']}), result['status_code']

    return jsonify({"error": "Unsupported provider type"}), 400

if __name__ == '__main__':
    ensure_dirs()
    print(f"Server started on http://127.0.0.1:5000")
    print(f"Project data: {os.path.abspath(DATA_DIR)}")
    app.run(debug=True, port=5000)
