import os
import sys

# ========================================================
# 强制定位到 EXE 真实目录
# ========================================================
def init_environment():
    # 1. 获取 EXE 所在的绝对路径
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 EXE，路径就是可执行文件所在的目录
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        # 如果是开发环境，路径就是代码所在目录
        BASE_DIR = os.path.abspath(".")

    # 2. [关键] 切换当前工作目录
    os.chdir(BASE_DIR)
    
    # 3. 确保目录存在 (防止用户误删导致报错)
    static_dir = os.path.join(BASE_DIR, 'static')
    data_dir = os.path.join(BASE_DIR, 'data')
    
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        print(f"Created missing static dir: {static_dir}")
        
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created missing data dir: {data_dir}")

    return BASE_DIR

# 执行初始化，并获取根目录路径
BASE_DIR = init_environment()

import time
import re
import uuid
import json
from typing import List, Optional, Dict, Any

import logging
from logging.handlers import RotatingFileHandler

# === 检测是否为打包后的 EXE 环境 ===
IS_FROZEN = getattr(sys, 'frozen', False)

# 只有在非 EXE 环境下，才加载 eventlet
# 在 EXE 桌面版环境下，我们要用 threading 模式，避免死锁
if IS_FROZEN:
    # === [核心修复] 显式导入 threading 驱动 ===
    import engineio.async_drivers.threading
else:
    # 开发环境使用 eventlet
    import eventlet
    eventlet.monkey_patch()

from flask import Flask, request, jsonify, send_file, after_this_request

import ai_service 
from data_manager import DataManager
from media_manager import MediaManager

from flask_socketio import SocketIO
from task_queue import queue, init_socketio

# ==========================================
# 日志配置 (输出到文件 + 自动切割)
# ==========================================
app_logger = None

def setup_logging():
    global app_logger
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'), 
        maxBytes=10*1024*1024, 
        backupCount=10, 
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.handlers = []
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.setLevel(logging.INFO)
    
    logging.getLogger('socketio').setLevel(logging.INFO)
    logging.getLogger('engineio').setLevel(logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    app_logger = root
    print(f"✅ 日志系统已接管。Werkzeug 默认日志已屏蔽，改用手动拦截。")

setup_logging()

# --- 配置 ---
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
app = Flask(__name__, static_url_path='/static', static_folder=STATIC_FOLDER)
app.config['SECRET_KEY'] = 'secret!'
socket_mode = 'threading' if IS_FROZEN else 'eventlet'
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode=socket_mode,
    logger=True,
    engineio_logger=True
)
init_socketio(socketio)

# 初始化管理器
db = DataManager() 
media_mgr = MediaManager(STATIC_FOLDER)

# --- 路由 ---
@app.after_request
def log_http_request(response):
    if request.path.startswith('/static') or request.path.startswith('/favicon'):
        return response
    ip = request.remote_addr
    method = request.method
    path = request.path
    status = response.status_code
    app_logger.info(f"[HTTP] {ip} - {method} {path} - {status}")
    return response

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    socketio.emit('task_update', queue.get_list())
    
@app.route('/')
def index(): return send_file('series.html')

@app.route('/series')
def index_series(): return send_file('series.html')

@app.route('/project')
def series_page(): return send_file('index.html')

# === Series API ===
@app.route('/api/series', methods=['GET'])
def get_all_series():
    return jsonify(db.get_all_series())

@app.route('/api/series', methods=['POST'])
def create_series():
    data = request.json
    if not data.get('name'): return jsonify({"error": "剧集名称必填"}), 400
    new_series = db.create_series(data)
    return jsonify(new_series), 201

@app.route('/api/series/<series_id>', methods=['PUT'])
def update_series(series_id):
    updated = db.update_series(series_id, request.json)
    if updated: return jsonify(updated)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/series/<series_id>', methods=['DELETE'])
def delete_series(series_id):
    db.delete_series(series_id)
    return jsonify({"success": True})

@app.route('/api/series/<series_id>/episodes', methods=['GET'])
def get_series_episodes(series_id):
    episodes = db.get_projects_by_series(series_id)
    return jsonify(episodes)

# === Settings API ===
@app.route('/api/settings', methods=['GET'])
def get_settings():
    data = db.get_settings()
    for p in data.get('providers', []):
        if p.get('api_key'): p['api_key'] = p['api_key'][:6] + '******'
    return jsonify(data.get('providers', []))

@app.route('/api/settings/provider', methods=['POST'])
def save_provider():
    req = request.json
    settings = db.get_settings()
    providers = settings.get('providers', [])
    
    provider_id = req.get('id') or str(uuid.uuid4())
    new_p = {
        'id': provider_id,
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
    db.save_settings(settings)
    return jsonify({"success": True, "id": new_p['id']})

@app.route('/api/settings/provider/<pid>', methods=['DELETE'])
def delete_provider(pid):
    settings = db.get_settings()
    settings['providers'] = [p for p in settings.get('providers', []) if p['id'] != pid]
    db.save_settings(settings)
    return jsonify({"success": True})

# === Project API ===
@app.route('/api/projects', methods=['GET'])
def get_projects():
    series_id_filter = request.args.get('series_id')
    if series_id_filter:
        projects = db.get_projects_by_series(series_id_filter)
    else:
        projects = db.get_all_projects()
    
    series_list = db.get_all_series()
    series_map = {s['id']: s['name'] for s in series_list}
    
    for p in projects:
        sid = p.get('series_id')
        if sid and sid in series_map:
            s_name = series_map[sid]
            p['series_name'] = s_name
            p['display_name'] = f"【{s_name}】{p.get('film_name', '')}"
        else:
            p['series_name'] = ""
            p['display_name'] = p.get('film_name', '未命名项目')
            
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    if not data.get('film_name'): return jsonify({"error": "项目名称必填"}), 400
    
    series_id = data.get('series_id')
    if series_id:
        series = db.get_series_by_id(series_id)
        if series:
            inherit_fields = [
                'script_core_conflict', 'script_emotional_keywords', 
                'basic_info', 'visual_color_system', 'visual_consistency_prompt'
            ]
            for field in inherit_fields:
                if not data.get(field) and series.get(field):
                    data[field] = series.get(field)

    project = db.create_project(data)
    return jsonify(project), 201

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    data = db.get_project(project_id)
    return jsonify(data) if data else (jsonify({"error": "Not found"}), 404)

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    updated = db.update_project(project_id, request.json)
    if updated: return jsonify(updated)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    success = db.delete_project(project_id)
    if success: return jsonify({"message": "Deleted"})
    return jsonify({"error": "Not found"}), 404

# === Script API ===
@app.route('/api/projects/<project_id>/script', methods=['GET'])
def get_script(project_id): 
    return jsonify(db.get_script(project_id))

@app.route('/api/projects/<project_id>/script', methods=['POST'])
def save_script(project_id):
    db.save_script(project_id, request.json)
    return jsonify({"success": True})

# === Shot API ===
@app.route('/api/projects/<project_id>/shots', methods=['GET'])
def get_shots(project_id): 
    return jsonify(db.get_shots(project_id))

@app.route('/api/projects/<project_id>/shots', methods=['POST'])
def create_shot(project_id):
    new_shot = db.create_shot(project_id, request.json)
    return jsonify(new_shot), 201

@app.route('/api/projects/<project_id>/shots/<shot_id>', methods=['PUT'])
def update_shot(project_id, shot_id):
    updated = db.update_shot(project_id, shot_id, request.json)
    if updated: return jsonify(updated)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/projects/<project_id>/shots/<shot_id>', methods=['DELETE'])
def delete_shot(project_id, shot_id):
    db.delete_shot(project_id, shot_id)
    return jsonify({"message": "Deleted"})

@app.route('/api/projects/<project_id>/shots/batch_delete', methods=['POST'])
def batch_delete_shots(project_id):
    ids = request.json.get('ids', [])
    db.batch_delete_shots(project_id, ids)
    return jsonify({"success": True})

@app.route('/api/projects/<project_id>/shots/reorder', methods=['POST'])
def reorder_shots(project_id):
    ordered_ids = request.json.get('shot_ids', [])
    db.reorder_shots(project_id, ordered_ids)
    return jsonify({"success": True})

# === AI & Export Services ===

@app.route('/api/generate/script_continuation', methods=['POST'])
def generate_script_continuation():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    sys = "你是一个专业的中文电影编剧助手。请根据前文续写一段剧本。要求：全中文，画面感强。"
    msgs = [{'role': 'system', 'content': sys}, {'role': 'user', 'content': f"前文：\n{data.get('context_text','')}\n\n请续写："}]
    
    result = ai_service.run_text_generation(msgs, config)
    return jsonify(result) if result.get('success') else (jsonify(result), 500)

@app.route('/api/generate/analyze_series', methods=['POST'])
def analyze_series():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    content = data.get('content', '')
    if not content:
        return jsonify({"error": "Content is empty"}), 400
        
    sys_prompt = """
    你是一位资深的影视策划人与视觉总监。请阅读用户提供的剧本片段或小说内容，提取关键信息并进行艺术加工，生成一份高质量的剧集立项方案。
    请严格返回一个纯 JSON 对象，包含以下字段：name, description, script_core_conflict, script_emotional_keywords, basic_info, visual_color_system, visual_consistency_prompt
    """
    
    user_prompt = f"剧本/小说内容如下：\n\n{content}"
    msgs = [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}]
    
    result = ai_service.run_text_generation(msgs, config)
    
    if result.get('success'):
        try:
            raw_content = result['content'].strip()
            cleaned = re.sub(r'^```json\s*|\s*```$', '', raw_content, flags=re.MULTILINE | re.DOTALL)
            parsed_data = json.loads(cleaned)
            return jsonify(parsed_data)
        except Exception as e:
            return jsonify({
                "description": result['content'], 
                "error": "Failed to parse JSON, returning raw text"
            })
            
    return jsonify(result), 500


@app.route('/api/generate/analyze_script', methods=['POST'])
def analyze_script():
    """
    [UPDATED] 基于 Cinematographer AI PDF Phase 2: 9-Shot Narrative Grid 逻辑
    目标：生成具有叙事纪律、无废镜头、节奏多变的分镜列表
    """
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    project_id = data.get('project_id')
    project_info = db.get_project(project_id) if project_id else {}
    character_list = db.get_characters(project_id) if project_id else []
    
    characters_info = ""
    if character_list:
        characters_info = "\n".join([f"- {char.get('name', '')}: {char.get('description', '')}" for char in character_list])
        characters_info = f"\n\n已有角色列表：\n{characters_info}"
    
    # === [Phase 2: 叙事纪律注入] ===
    sys = f"""
    你是一位专家级动漫电影摄影师 (Cinematographer AI)。你的任务是将剧本转化为极具张力的动漫电影分镜表。

    【CRITICAL: Storytelling Discipline / 叙事纪律】
    1. **拒绝废镜头**: 每一帧都必须提出问题或回答问题。如果镜头没有建立张力、揭示信息或转换情绪，就删掉它。
    2. **避免重复**: 不要连续使用相似的景别。交替使用宽景 (Context) 和特写 (Detail) 来控制节奏。
    3. **多样的机位**: 混合使用极远景、中景、特写、细节特写、低角度 (Power)、高角度 (Vulnerability)、过肩镜头等。
    4. **物理与情感弧光**: 角色在空间中的移动应反映其心理状态 (例如：行走->跪下 = 自信->脆弱)。
    5. **明确性**: 描述必须精准，明确谁在画面中、在哪里、做什么，不允许模糊不清。
    6. **以静制动**: 对于后续视频生成，明确哪些镜头适合静止（张力），哪些适合动态（动作）。

    **输出要求**：
    1. 返回一个纯 JSON 数组。
    2. **必须使用中文**填写所有描述性字段。
    3. 不要包含 Markdown 标记。
    **JSON对象结构**：scene (场号), shot_number (镜号), visual_description (视觉画面描述), scene_description (场景环境), characters (列表), dialogue, audio_description, shot_size (景别: 远景/全景/中景/特写/特写细节), camera_movement (运镜: 推/拉/摇/移/跟随/手持/静止), duration (秒)
    """
    user_prompt = f"""
        剧本内容：{data.get('content', '')}
        人物信息：{characters_info}
        项目基础信息：{project_info.get('basic_info', '')}
        情感关键词：{project_info.get('script_emotional_keywords', '')}
        色彩体系：{project_info.get('visual_color_system', '')}
    """

    msgs = [{'role': 'system', 'content': sys}, {'role': 'user', 'content': user_prompt}]
    result = ai_service.run_text_generation(msgs, config)
    
    if result.get('success'):
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', result['content'].strip(), flags=re.MULTILINE | re.DOTALL)
            shots_data = json.loads(cleaned)
            
            current_char_list = db.get_characters(project_id) if project_id else []

            def map_character_names(names, char_data_list, pid):
                mapped_objs = []
                if isinstance(names, str): names = [names]
                if not isinstance(names, list): return []
                for name in names:
                    if not name: continue
                    clean_name = str(name).strip()
                    if not clean_name: continue
                    found = next((c for c in char_data_list if c.get('name', '').strip() == clean_name), None)
                    if found:
                        mapped_objs.append(found)
                    else:
                        new_char_data = {'name': clean_name, 'description': 'AI 剧本分析自动识别的新角色'}
                        saved_char = db.create_character(pid, new_char_data)
                        char_data_list.append(saved_char)
                        mapped_objs.append(saved_char)
                return mapped_objs

            for shot in shots_data:
                if 'characters' in shot:
                    shot['characters'] = map_character_names(shot['characters'], current_char_list, project_id)

            return jsonify({'shots': shots_data})
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Invalid JSON from AI', 'details': str(e)}), 500
            
    return jsonify(result), 500

@app.route('/api/generate/image', methods=['POST'])
def generate_image():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    shot_id = data.get('shot_id')
    pid = data.get('project_id')
    
    current_shot = db.get_shot(pid, shot_id)
    if not current_shot: return jsonify({"error": "Shot not found"}), 404
    
    prev_shot = db.get_previous_shot(pid, current_shot.get('shot_number'))
    prev_context = prev_shot['end_frame_prompt'] if prev_shot else ''
    start_prompt_ref = current_shot.get('start_frame_prompt')
    
    result, used_prompt = ai_service.run_image_generation(
        data.get('visual_description'), data.get('style_description'), data.get('consistency_text'),
        data.get('frame_type'), config, media_mgr, start_prompt_ref, prev_context, entity_id=shot_id
    )

    if result.get('success'):
        update_data = {'start_frame_prompt': used_prompt} if data.get('frame_type') == 'start' else {'end_frame_prompt': used_prompt}
        db.update_shot(pid, shot_id, update_data)
        return jsonify(result)
    return jsonify(result), 500


@app.route('/api/projects/<project_id>/export/jianying', methods=['POST'])
def export_jianying(project_id):
    project_info = db.get_project(project_id)
    from jianying_exporter import export_draft
    
    raw_fusions = db.get_fusions(project_id)
    export_dir = os.path.join(STATIC_FOLDER, "exports")
    result = export_draft(project_info, raw_fusions, STATIC_FOLDER, export_dir)
    
    if result['success']:
        zip_path = result['zip_path']
        filename = os.path.basename(zip_path)
        return send_file(zip_path, as_attachment=True, download_name=filename, mimetype='application/zip')
    else:
        return jsonify(result), 500

# === Character API ===
@app.route('/api/projects/<project_id>/characters', methods=['GET'])
def get_characters(project_id):
    return jsonify(db.get_characters(project_id))

@app.route('/api/projects/<project_id>/characters', methods=['POST'])
def create_character(project_id):
    new_char = db.create_character(project_id, request.json)
    return jsonify(new_char), 201

@app.route('/api/projects/<project_id>/characters/<character_id>', methods=['PUT'])
def update_character(project_id, character_id):
    updated = db.update_character(project_id, character_id, request.json)
    if updated: return jsonify(updated)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/projects/<project_id>/characters/<character_id>', methods=['DELETE'])
def delete_character(project_id, character_id):
    db.delete_character(project_id, character_id)
    return jsonify({"message": "Deleted"})

@app.route('/api/generate/character_views', methods=['POST'])
def generate_character_views():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')

    project_id = data.get('project_id')
    character_id = data.get('character_id')
    
    project_info = db.get_project(project_id) if project_id else {}
    
    prompt = build_comprehensive_character_prompt(
        data.get('character_description'), 
        project_info.get('visual_color_system', ''), 
        project_info.get('script_emotional_keywords', ''), 
        project_info.get('basic_info', '')
    )
    
    result = ai_service.run_simple_image_generation(prompt, config, media_mgr, entity_id=character_id)
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False, 'error': '生成失败'}), 500)

def build_comprehensive_character_prompt(character_desc, color_system, emotional_keywords, basic_info):
    """
    [UPDATED] 基于 PDF Phase 1: Character Foundation 逻辑
    重点：视频一致性 (Video Consistency)，简单轮廓，无琐碎细节
    """
    prompt = f"""
    [Cinematographer AI Character Reference]
    主体：{character_desc}
    
    【CRITICAL: Design for Video Consistency / 视频生成一致性设计】
    1. **简化设计 (SIMPLE)**: 保持角色轮廓清晰简洁。
    2. **拒绝琐碎细节**: 避免任何细小的悬挂元素（如流苏、细链条、飘带、羊皮纸碎片），这些在视频生成中会变成噪点。
    3. **标志性形状**: 强调可识别的形状（如独特的头盔轮廓、大胆的护甲设计）。
    4. **电影级写实**: 追求超写实摄影质感 (Hyper-realistic photography)，而非概念艺术。
    
    请生成一张包含以下内容的角色设计表 (Character Sheet)：
    1. 左上角：角色正面特写 (Chest up)
    2. 右上角：角色正面全身
    3. 左下角：角色侧面全身
    4. 右下角：角色背面全身
    
    重要要求：纯白背景，无水印，人物外貌特征在所有视图中保持严格一致。
    """
    if color_system: prompt += f"\n色彩体系：{color_system} (保持电影感色调)"
    if emotional_keywords: prompt += f"\n情感/能量状态：{emotional_keywords}"
    if basic_info: prompt += f"\n背景设定：{basic_info}"
    return prompt

@app.route('/api/generate/character_list', methods=['POST'])
def generate_character_list():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')

    visual_prompt = data.get('visual_consistency_prompt', '')
    sys = "你是一个专业的电影角色设计师。请根据提供的视觉统一设定，生成主要角色列表，每个角色包含名称和详细描述。"
    msgs = [{'role': 'system', 'content': sys}, 
            {'role': 'user', 'content': f"视觉统一设定：{visual_prompt}\n\n请生成JSON格式的角色列表: {{ \"characters\": [ {{\"name\": \"...\", \"description\": \"...\"}} ] }}"}]

    result = ai_service.run_text_generation(msgs, config)
    if result.get('success'):
        try:
            json_match = re.search(r'\{.*\}', result.get('content', ''), re.DOTALL)
            if json_match:
                character_data = json.loads(json_match.group(0))
                return jsonify({'success': True, 'characters': character_data.get('characters', [])})
        except: pass
    return jsonify({'success': False, 'error': '无法解析角色列表'}), 500

@app.route('/api/upload/character_image', methods=['POST'])
def upload_character_image():
    if 'file' not in request.files: return jsonify({'success': False, 'error': 'No file'}), 400
    cid = request.form.get('character_id') or 'char'
    url, err = media_mgr.save_uploaded_file(request.files['file'], media_type='image', entity_id=cid)
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/projects/<project_id>/characters/batch_delete', methods=['POST'])
def batch_delete_characters(project_id):
    ids = request.json.get('ids', [])
    if not ids: return jsonify({"success": True})
    for cid in ids: db.delete_character(project_id, cid)
    return jsonify({"success": True})

@app.route('/api/upload/scene_image', methods=['POST'])
def upload_scene_image():
    if 'file' not in request.files: return jsonify({'success': False, 'error': 'No file'}), 400
    sid = request.form.get('scene_id') or 'scene'
    url, err = media_mgr.save_uploaded_file(request.files['file'], media_type='image', entity_id=sid)
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/upload/grid_image', methods=['POST'])
def upload_grid_image():
    if 'file' not in request.files: return jsonify({'success': False, 'error': 'No file'}), 400
    sid = request.form.get('shot_id') or 'scene'
    url, err = media_mgr.save_uploaded_file(request.files['file'], media_type='image', entity_id=sid)
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/generate/scene_prompt', methods=['POST'])
def generate_scene_prompt():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    project_id = data.get('project_id')
    project_info = db.get_project(project_id) if project_id else {}
    
    sys = "你是一个专业的电影场景设计师。请根据场景描述生成详细的场景提示词。"
    user_prompt = f"场景描述：{data.get('scene_description')}\n请生成包含时间、天气、光影、空间、风格的详细提示词。"
    
    if project_info:
        user_prompt += f"\n色彩：{project_info.get('visual_color_system','')}\n基调：{project_info.get('script_emotional_keywords','')}"

    result = ai_service.run_text_generation([{'role': 'system', 'content': sys}, {'role': 'user', 'content': user_prompt}], config)
    return jsonify({'success': True, 'prompt': result['content']}) if result.get('success') else (jsonify({'success': False}), 500)

@app.route('/api/generate/scene_image', methods=['POST'])
def generate_scene_image():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    scene_id = data.get('scene_id')
    prompt = f"电影场景设计图，{data.get('scene_prompt')}。高分辨率，电影质感。"
    result = ai_service.run_simple_image_generation(prompt, config, media_mgr, entity_id=scene_id)
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False}), 500)

# === Fusion API ===
@app.route('/api/projects/<project_id>/fusions', methods=['GET'])
def get_fusions(project_id):
    return jsonify(db.get_fusions(project_id))

@app.route('/api/projects/<project_id>/fusions', methods=['POST'])
def create_fusion(project_id):
    return jsonify(db.create_fusion(project_id, request.json)), 201

@app.route('/api/projects/<project_id>/fusions/<fusion_id>', methods=['PUT'])
def update_fusion(project_id, fusion_id):
    updated = db.update_fusion(project_id, fusion_id, request.json)
    if updated: return jsonify(updated)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/projects/<project_id>/fusions/<fusion_id>', methods=['DELETE'])
def delete_fusion(project_id, fusion_id):
    db.delete_fusion(project_id, fusion_id)
    return jsonify({"message": "Deleted"})

@app.route('/api/generate/element_image', methods=['POST'])
def generate_element_image():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    element_id = data.get('element_id')
    result = ai_service.run_simple_image_generation(data.get('prompt'), config, media_mgr, entity_id=element_id)
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False}), 500)

@app.route('/api/upload/element_image', methods=['POST'])
def upload_element_image():
    if 'file' not in request.files: return jsonify({'success': False}), 400
    eid = request.form.get('element_id')
    url, err = media_mgr.save_uploaded_file(request.files['file'], media_type='image', entity_id=eid)
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/upload/base_image', methods=['POST'])
def upload_base_image():
    if 'file' not in request.files: return jsonify({'success': False}), 400
    fid = request.form.get('fusion_id')
    url, err = media_mgr.save_uploaded_file(request.files['file'], media_type='image', entity_id=fid)
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/generate/fusion_image', methods=['POST'])
def generate_fusion_image():
    data = request.json
    fusion_id = data.get('fusion_id')
    project_id = data.get('project_id')
    
    current_fusion = db.get_fusion(project_id, fusion_id)
    if not current_fusion: return jsonify({'success': False, 'error': 'Fusion not found'}), 404
    
    base_image_url = current_fusion.get('base_image')
    if not base_image_url: return jsonify({'success': False, 'error': 'No base image'}), 400
    
    base_image_path = media_mgr.get_absolute_path(base_image_url)
    
    element_paths = []
    for el in current_fusion.get('elements', []):
        if el.get('image_url'): 
            element_paths.append(media_mgr.get_absolute_path(el['image_url']))
        
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    result = ai_service.run_fusion_generation(
        base_image_path=base_image_path,
        fusion_prompt=data.get('fusion_prompt'),
        config=config,
        media_manager=media_mgr,
        element_image_paths=element_paths,
        entity_id=fusion_id
    )
    
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False, 'error': result.get('error_msg')}), 500)

@app.route('/api/generate/fusion_prompt', methods=['POST'])
def generate_fusion_prompt():
    """
    [UPDATED] 基于 PDF Phase 3 Logic: Image-to-Video Motion Prompts Prep
    目标：生成 Explicit Shot Description, 并包含 Environmental Motion (如 fog, wind) 以为视频做准备
    """
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    project_info = db.get_project(data.get('project_id')) if data.get('project_id') else {}
    
    # === [Phase 3: Motion Prep & Explicit Description] ===
    sys = """
    你是一位专家级电影摄影师 (Cinematographer AI)。请生成用于 AI 图像生成的英文提示词。
    
    【Output Format - Strict】
    [Subject Description] + [Shot Setup] + [Environment/Lighting] + [Style Keywords]
    
    【Principles】
    1. **Shot Description Clarity**: 极其明确地描述谁在画面中、在哪个位置、面朝哪里。不要留给 AI 猜测的空间。
    2. **Realism**: 追求《你的名字》的动漫二次元感，避免由于描述模糊导致的概念图质感。
    3. **Motion Prep (重要)**: 既然这是为视频生成的静帧，请在环境描述中包含动态元素 (如 drifting fog, swaying branches, dust particles)，这能让后续的图生视频更生动。
    
    请直接输出中文提示词，不要包含 Markdown 或其他解释性文字。
    """
    
    base_info = f"【元素结合】：{data.get('element_mapping')} 【场景环境】：{data.get('scene_description')} 【镜头动作】：{data.get('shot_description')}"
    if project_info: user_prompt_base = f"{base_info}\n【整体色彩体系】：{project_info.get('visual_color_system','')}"
    else: user_prompt_base = base_info

    # 生成首帧
    user_prompt_start = f"{user_prompt_base}\n\n任务：生成该镜头 **开始时刻 (Start Frame)** 的画面提示词。"
    res_start = ai_service.run_text_generation([{'role': 'system', 'content': sys}, {'role': 'user', 'content': user_prompt_start}], config)
    
    # 生成尾帧 (为视频一致性做准备)
    user_prompt_end = f"{user_prompt_base}\n\n任务：生成该镜头 **结束时刻 (End Frame)** 的画面提示词。如果镜头有推拉摇移，请描述视角的改变；如果角色有动作，请描述动作完成后的状态。"
    res_end = ai_service.run_text_generation([{'role': 'system', 'content': sys}, {'role': 'user', 'content': user_prompt_end}], config)
    
    if res_start.get('success'):
        return jsonify({'success': True, 'prompt': res_start['content'], 'end_frame_prompt': res_end.get('content', '')})
    return jsonify({'success': False}), 500

@app.route('/api/generate/fusion_video', methods=['POST'])
def generate_fusion_video():
    """
    [UPDATED] PDF Phase 3: Motion Generation
    注意：虽然这里调用的是视频生成模型，但输入的 Prompt (来自 fusion_prompt) 必须包含 PDF 中提到的 Motion Keywords。
    """
    data = request.json
    fusion_id = data.get('fusion_id')
    project_id = data.get('project_id')
    
    current_fusion = db.get_fusion(project_id, fusion_id)
    if not current_fusion: return jsonify({'success': False, 'error': 'Not found'}), 404
    
    s_url = current_fusion.get('result_image')
    e_url = current_fusion.get('end_frame_image')
    if not s_url: return jsonify({'success': False, 'error': 'No start image'}), 400
    
    s_path = media_mgr.get_absolute_path(s_url)
    e_path = media_mgr.get_absolute_path(e_url) if e_url else None
    
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    # 获取提示词，如果没有则给默认值。
    # 理想情况下，这里的 fusion_prompt 已经由上面的 generate_fusion_prompt 生成并包含 Motion keywords
    prompt_text = current_fusion.get('fusion_prompt') or "high quality cinematic video, slow motion"
    
    result = ai_service.run_video_generation(
        prompt_text,
        s_path, e_path, config, 
        media_mgr,
        entity_id=fusion_id
    )
    
    if result.get('success'):
        db.update_fusion(project_id, fusion_id, {'video_url': result['url']})
        return jsonify({'success': True, 'url': result['url']})
    return jsonify({'success': False}), 500

@app.route('/api/projects/<project_id>/history', methods=['GET'])
def get_project_history(project_id):
    entity_map = {}
    
    chars = db.get_characters(project_id)
    for c in chars:
        entity_map[c['id']] = {'name': f"角色: {c['name']}", 'type': 'character'}
        
    shots = db.get_shots(project_id)
    for s in shots:
        name = f"场{s.get('scene','?')}-镜{s.get('shot_number','?')}"
        entity_map[s['id']] = {'name': name, 'type': 'shot'}
        
    fusions = db.get_fusions(project_id)
    for f in fusions:
        name = f"融图: 场{f.get('scene','?')}-镜{f.get('shot_number','?')}"
        entity_map[f['id']] = {'name': name, 'type': 'fusion'}
        if f.get('elements'):
            for el in f['elements']:
                if el.get('id'):
                    entity_map[el['id']] = {'name': f"元素: {el.get('name')} ({name})", 'type': 'element'}

    history_list = media_mgr.scan_project_files(entity_map)
    print(history_list)
    return jsonify(history_list)

@app.route('/api/generate/analyze_image', methods=['POST'])
def analyze_uploaded_image():
    if 'file' not in request.files: return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'success': False, 'error': 'No file selected'}), 400

    temp_id = f"analysis_{uuid.uuid4().hex[:8]}"
    url, err = media_mgr.save_uploaded_file(file, media_type='image', entity_id=temp_id)
    if err: return jsonify({'success': False, 'error': err}), 500
    
    image_abs_path = media_mgr.get_absolute_path(url)

    VISUAL_STYLE_PROMPT = """
    请作为一个专业的电影美术指导与摄影指导分析这张图片。
    请忽略图片中的具体剧情内容，重点提取画面的【视觉风格要素】，以便我将其作为Prompt输入给AI绘画工具来复制这种风格。
    请严格按照以下维度进行提取和描述：
    1. **艺术风格/流派** (Art Style)
    2. **光影与氛围** (Lighting & Atmosphere)
    3. **色彩体系** (Color Palette)
    4. **材质与渲染质感** (Texture & Rendering)
    最后，请将上述分析汇总为一段连贯的、高质量的中文Prompt描述。
    """

    config = None
    settings = db.get_settings()
    for p in settings.get('providers', []):
        if p.get('type') == 'aliyun' and p.get('enabled', True):
            config = p
            break
    
    if not config: return jsonify({'success': False, 'error': 'No Aliyun provider configuration found.'}), 400
    
    result = ai_service.run_visual_analysis(image_abs_path, VISUAL_STYLE_PROMPT, config, media_mgr)
    
    if result.get('success'):
        return jsonify({
            'success': True, 
            'style_description': result['content'],
            'image_url': url
        })
    else:
        return jsonify(result), 500

from task_queue import queue
from async_bridge import context_runner

@app.route('/api/async/generate/fusion_image', methods=['POST'])
def async_fusion_image():
    data = request.json
    pid = data.get('project_id')
    fid = data.get('fusion_id')
    
    def save_logic(result):
        is_end = 'end_frame_prompt' in data and data['end_frame_prompt']
        field = 'end_frame_image' if is_end else 'result_image'
        db.update_fusion(pid, fid, {field: result['url']})
        print(f"💾 [后台] 已更新融图 {fid} 的 {field}")

    queue.submit(
        context_runner, app, generate_fusion_image, data, save_logic,
        desc=f"融图生成 ({fid})"
    )
    return jsonify({"success": True, "status": "queued"})

@app.route('/api/async/generate/scene_image', methods=['POST'])
def async_scene_image():
    data = request.json
    pid = data.get('project_id')
    sid = data.get('scene_id')

    save_logic = lambda res: db.update_shot(pid, sid, {'scene_image': res['url']})

    queue.submit(
        context_runner, app, generate_scene_image, data, save_logic,
        desc=f"场景图生成 ({sid})"
    )
    return jsonify({"success": True, "status": "queued"})

@app.route('/api/async/generate/fusion_video', methods=['POST'])
def async_fusion_video():
    data = request.json
    pid = data.get('project_id')
    fid = data.get('fusion_id')

    save_logic = lambda res: db.update_fusion(pid, fid, {'video_url': res['url']})

    queue.submit(
        context_runner, app, generate_fusion_video, data, save_logic,
        desc=f"视频生成 ({fid})"
    )
    return jsonify({"success": True, "status": "queued"})

@app.route('/api/async/generate/character_views', methods=['POST'])
def async_character_views():
    data = request.json
    pid = data.get('project_id')
    cid = data.get('character_id')

    def save_logic(result):
        if result.get('url'):
            db.update_character(pid, cid, {'image_url': result['url']})
            print(f"💾 [后台] 已更新角色 {cid} 的 image_url")

    queue.submit(
        context_runner, app, generate_character_views, data, save_logic,
        desc=f"角色设计图 ({cid})"
    )
    return jsonify({"success": True, "status": "queued"})

@app.route('/api/async/generate/scene_prompt', methods=['POST'])
def async_scene_prompt():
    data = request.json
    pid = data.get('project_id')
    sid = data.get('scene_id') or data.get('shot_id') 

    def save_logic(result):
        if result.get('prompt'):
            db.update_shot(pid, sid, {'scene_prompt': result['prompt']})
            print(f"📝 [后台] 已更新场景 {sid} 的提示词")

    queue.submit(
        context_runner, app, generate_scene_prompt, data, save_logic,
        desc=f"场景提示词 ({sid})"
    )
    return jsonify({"success": True, "status": "queued"})

@app.route('/api/async/generate/fusion_prompt', methods=['POST'])
def async_fusion_prompt():
    data = request.json
    pid = data.get('project_id')
    fid = data.get('fusion_id') or data.get('id')

    def save_logic(result):
        updates = {}
        if result.get('prompt'): updates['fusion_prompt'] = result['prompt']
        if result.get('end_frame_prompt'): updates['end_frame_prompt'] = result['end_frame_prompt']
        if updates:
            db.update_fusion(pid, fid, updates)
            print(f"📝 [后台] 已更新融图 {fid} 的提示词")

    queue.submit(
        context_runner, app, generate_fusion_prompt, data, save_logic,
        desc=f"融图提示词 ({fid})"
    )
    return jsonify({"success": True, "status": "queued"})

# ----------------------------------------------------
# 9宫格 (Grid) 相关 Controller
# ----------------------------------------------------

@app.route('/api/generate/grid_prompt', methods=['POST'])
def generate_grid_prompt():
    """
    生成用于 9宫格 角色动作分镜的 Prompt
    """
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    # 构造 Prompt
    # 核心是将 scene_description, visual_description, characters 结合
    # 要求生成一个 3x3 grid 的描述
    
    scene_desc = data.get('scene_description', '')
    shot_desc = data.get('shot_description', '')
    char_names = data.get('character_names', []) # list of names
    
    sys_prompt = """
    你是一位资深分镜师。请根据输入生成一段用于 AI 绘画的英文 Prompt。
    
    【目标】生成一张 **3x3 分镜九宫格 (9-panel storyboard grid)**，展示角色在特定场景中的连续动作或不同景别。
    
    【格式要求】
    必须用中文回答. 
    结果: "一种 3×3 的分镜网格布局。【场景与灯光】。【角色】的连续性动作：【动作描述】。呈现【细节】的关键帧画面"
    
    请确保 Prompt 强调 "9 格画面", "形象连贯的角色", "顺序叙事逻辑".
    """
    
    user_prompt = f"""
    场景：{scene_desc}
    动作：{shot_desc}
    角色：{', '.join(char_names)}
    """
    
    result = ai_service.run_text_generation(
        [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}], 
        config
    )
    
    return jsonify({'success': True, 'prompt': result['content']}) if result.get('success') else (jsonify({'success': False}), 500)


@app.route('/api/generate/grid_image', methods=['POST'])
def generate_grid_image():
    """
    生成 9宫格 图片
    使用 run_fusion_generation (Image-to-Image) 或 run_simple_image_generation (Text-to-Image)
    这里假设使用 Image-to-Image，将 Scene Image 作为 Base，或者 Text-to-Image 仅用 Prompt
    根据用户需求 "将底图和人物列表作为融图的素材"，最好是 Image-to-Image (ControlNet or Ref)
    但为了简化，我们复用 run_fusion_generation 的逻辑，将 Scene Image 设为 Base Image
    """
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    shot_id = data.get('shot_id')
    # 这里的 grid_prompt 应该是上面生成的 "A 3x3 storyboard grid..."
    prompt = data.get('grid_prompt') 
    
    # 获取底图路径
    base_image_url = data.get('base_image_url')
    base_image_path = media_mgr.get_absolute_path(base_image_url) if base_image_url else None
    
    # 获取角色图路径列表
    # character_images: list of urls
    element_paths = []
    for url in data.get('character_images', []):
        if url:
            element_paths.append(media_mgr.get_absolute_path(url))
            
    # 调用 AI Service
    # 如果有 base_image, 倾向于使用 fusion 生成 (img2img / controlnet)
    # 否则使用 simple generation (txt2img)
    if base_image_path:
        result = ai_service.run_fusion_generation(
            base_image_path=base_image_path,
            fusion_prompt=prompt,
            config=config,
            media_manager=media_mgr,
            element_image_paths=element_paths,
            entity_id=shot_id
        )
    else:
        # Fallback to text-to-image if no scene image
        result = ai_service.run_simple_image_generation(
            prompt, config, media_mgr, entity_id=shot_id
        )
        
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False, 'error': result.get('error_msg')}), 500)


@app.route('/api/async/generate/grid_image', methods=['POST'])
def async_grid_image():
    data = request.json
    pid = data.get('project_id')
    sid = data.get('shot_id')
    
    def save_logic(result):
        if result.get('url'):
            db.update_shot(pid, sid, {'grid_image': result['url']})
            print(f"💾 [后台] 已更新分镜 {sid} 的 9宫格图")

    queue.submit(
        context_runner, app, generate_grid_image, data, save_logic,
        desc=f"九宫格生成 ({sid})"
    )
    return jsonify({"success": True, "status": "queued"})

@app.route('/api/generate/video_prompt', methods=['POST'])
def generate_video_prompt():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    scene_desc = data.get('scene_description', '')
    shot_desc = data.get('shot_description', '')
    
    # todo 提示词还需要修改适配9宫格
    sys_prompt = """
    你是一位专业的视频生成提示词专家。请根据场景和画面描述，生成一段用于 AI 视频生成的中文 Prompt。
    
    【要求】
    1. 必须是中文。
    2. 重点描述 **动态 (Motion)**：包括运镜 (Camera Movement)、角色动作 (Subject Action)、环境动态 (Environmental Motion like wind, rain, light changes)。
    3. 格式建议: "[Subject & Action]. [Environment & Atmosphere]. [Camera Movement]. [Style]"
    """
    
    user_prompt = f"""
    场景描述：{scene_desc}
    分镜画面：{shot_desc}
    """
    
    result = ai_service.run_text_generation(
        [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}], 
        config
    )
    
    return jsonify({'success': True, 'prompt': result['content']}) if result.get('success') else (jsonify({'success': False}), 500)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(queue.get_list())

@app.route('/api/tasks/<tid>', methods=['DELETE'])
def delete_task(tid):
    if tid in queue.tasks: 
        del queue.tasks[tid]
        queue._emit_update()
    return jsonify({"success": True})

if __name__ == '__main__':
    print(f"Server started on http://127.0.0.1:5000")
    socketio.run(app, debug=True, port=5000)