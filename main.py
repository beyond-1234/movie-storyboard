import os
import time
import re
import uuid
from typing import List, Optional, Dict, Any
from flask import Flask, request, jsonify, send_file
from pathlib import Path

import ai_service 
from jianying_exporter import export_draft
from data_manager import DataManager

# --- 配置 ---
STATIC_FOLDER = "."
IMG_SAVE_DIR = "static/imgs"
VIDEO_SAVE_DIR = "static/videos"
AUDIO_SAVE_DIR = "static/audio"
EXPORT_DIR = "exports"

app = Flask(__name__, static_url_path='', static_folder=STATIC_FOLDER)
db = DataManager() # 初始化数据管理器

# --- 基础工具 ---
def ensure_static_dirs():
    for d in [IMG_SAVE_DIR, VIDEO_SAVE_DIR, AUDIO_SAVE_DIR, EXPORT_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)

# --- 路由 ---
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
    # Mask API keys
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
    return jsonify(db.get_all_projects())

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    if not data.get('film_name'): return jsonify({"error": "项目名称必填"}), 400
    
    # 继承 Series 数据的业务逻辑
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

@app.route('/api/generate/analyze_script', methods=['POST'])
def analyze_script():
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
    
    sys = f"""
    你是一个专业的电影分镜设计师。请根据剧本内容，生成详细的分镜列表，每个分镜包含场景说明和角色信息。
    **输出要求**：1. 返回一个纯 JSON 数组。2. **必须使用中文**填写所有描述性字段。3. 不要包含 Markdown 标记。
     **JSON对象结构**：scene, shot_number, visual_description, scene_description, characters, dialogue, audio_description, special_technique, duration
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
            # 辅助函数
            def map_character_names(names, char_data):
                mapped = []
                for name in names:
                    found = next((c for c in char_data if c.get('name') == name), None)
                    mapped.append(found if found else {'name': name, 'description': '新角色', 'id': str(uuid.uuid4())})
                return mapped

            for shot in shots_data:
                if 'characters' in shot:
                    shot['characters'] = map_character_names(shot['characters'], character_list)
            return jsonify({'shots': shots_data})
        except Exception as e:
            return jsonify({'error': 'Invalid JSON from AI'}), 500
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
    
    save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
    web_prefix = f"/{IMG_SAVE_DIR}"

    result, used_prompt = ai_service.run_image_generation(
        data.get('visual_description'), data.get('style_description'), data.get('consistency_text'),
        data.get('frame_type'), config, save_dir, web_prefix, start_prompt_ref, prev_context
    )

    if result.get('success'):
        update_data = {'start_frame_prompt': used_prompt} if data.get('frame_type') == 'start' else {'end_frame_prompt': used_prompt}
        db.update_shot(pid, shot_id, update_data)
        return jsonify(result)
    return jsonify(result), 500

@app.route('/api/generate/video', methods=['POST'])
def generate_video():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
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
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    save_dir = os.path.join(STATIC_FOLDER, AUDIO_SAVE_DIR)
    web_prefix = f"/{AUDIO_SAVE_DIR}"
    
    result = ai_service.run_voice_generation(data.get('text'), config, save_dir, web_prefix)
    return jsonify(result) if result.get('success') else (jsonify(result), 500)

@app.route('/api/projects/<project_id>/export/jianying', methods=['POST'])
def export_jianying(project_id):
    project_info = db.get_project(project_id)
    shots = db.get_shots(project_id)
    result = export_draft(project_info, shots, STATIC_FOLDER, EXPORT_DIR)
    return jsonify(result) if result['success'] else (jsonify(result), 500)

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
    save_dir = os.path.join(STATIC_FOLDER, IMG_SAVE_DIR)
    web_prefix = f"/{IMG_SAVE_DIR}"
    
    project_info = db.get_project(project_id) if project_id else {}
    
    prompt = build_comprehensive_character_prompt(
        data.get('character_description'), 
        project_info.get('visual_color_system', ''), 
        project_info.get('script_emotional_keywords', ''), 
        project_info.get('basic_info', '')
    )
    
    result = ai_service.run_simple_image_generation(prompt, config, save_dir, web_prefix)
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False, 'error': '生成失败'}), 500)

def build_comprehensive_character_prompt(character_desc, color_system, emotional_keywords, basic_info):
    prompt = f"电影角色设计图，{character_desc}。\n请生成一张包含以下内容的角色设计图：\n1. 左上角：角色正面特写\n2. 右上角：角色正面全身\n3. 左下角：角色侧面全身\n4. 右下角：角色背面全身\n重要要求：纯白背景，无水印，人物一致性。"
    if color_system: prompt += f"\n色彩体系：{color_system}"
    if emotional_keywords: prompt += f"\n情感基调：{emotional_keywords}"
    if basic_info: prompt += f"\n背景设定：{basic_info}"
    return prompt

@app.route('/api/generate/character_list', methods=['POST'])
def generate_character_list():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')

    visual_prompt = data.get('visual_consistency_prompt', '')
    sys = "你是一个专业的电影角色设计师。请根据提供的视觉统一设定，生成3-5个主要角色列表，每个角色包含名称和详细描述。"
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

# --- File Upload Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def save_uploaded_file(file, prefix_id, sub_dir=IMG_SAVE_DIR):
    if not file or not allowed_file(file.filename): return None, "Invalid file"
    ext = os.path.splitext(file.filename)[1].lower() or '.png'
    filename = f"{prefix_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_dir = os.path.join(STATIC_FOLDER, sub_dir)
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, filename)
    file.save(file_path)
    return f"/{sub_dir}/{filename}", None

@app.route('/api/upload/character_image', methods=['POST'])
def upload_character_image():
    if 'file' not in request.files: return jsonify({'success': False, 'error': 'No file'}), 400
    cid = request.form.get('character_id') or 'char'
    url, err = save_uploaded_file(request.files['file'], f"character_{cid}")
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/upload/scene_image', methods=['POST'])
def upload_scene_image():
    if 'file' not in request.files: return jsonify({'success': False, 'error': 'No file'}), 400
    sid = request.form.get('scene_id') or 'scene'
    url, err = save_uploaded_file(request.files['file'], f"scene_{sid}")
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
    
    prompt = f"电影场景设计图，{data.get('scene_prompt')}。高分辨率，电影质感。"
    result = ai_service.run_simple_image_generation(prompt, config, os.path.join(STATIC_FOLDER, IMG_SAVE_DIR), f"/{IMG_SAVE_DIR}")
    
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
    
    result = ai_service.run_simple_image_generation(data.get('prompt'), config, os.path.join(STATIC_FOLDER, IMG_SAVE_DIR), f"/{IMG_SAVE_DIR}")
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False}), 500)

@app.route('/api/upload/element_image', methods=['POST'])
def upload_element_image():
    if 'file' not in request.files: return jsonify({'success': False}), 400
    url, err = save_uploaded_file(request.files['file'], f"fusion_element")
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/upload/base_image', methods=['POST'])
def upload_base_image():
    if 'file' not in request.files: return jsonify({'success': False}), 400
    url, err = save_uploaded_file(request.files['file'], f"fusion_base")
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
    
    base_image_path = os.path.join(STATIC_FOLDER, base_image_url.lstrip('/'))
    
    element_paths = []
    for el in current_fusion.get('elements', []):
        if el.get('image_url'): element_paths.append(os.path.join(STATIC_FOLDER, el['image_url'].lstrip('/')))
        
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    result = ai_service.run_fusion_generation(
        base_image_path=base_image_path,
        fusion_prompt=data.get('fusion_prompt'),
        config=config,
        save_dir=os.path.join(STATIC_FOLDER, IMG_SAVE_DIR),
        url_prefix=f"/{IMG_SAVE_DIR}",
        element_image_paths=element_paths
    )
    
    return jsonify({'success': True, 'url': result['url']}) if result.get('success') else (jsonify({'success': False, 'error': result.get('error_msg')}), 500)

@app.route('/api/generate/fusion_prompt', methods=['POST'])
def generate_fusion_prompt():
    data = request.json
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    project_info = db.get_project(data.get('project_id')) if data.get('project_id') else {}
    
    sys = "你是一个专业的电影分镜设计师。请根据场景描述生成详细的融合图片提示词。"
    user_prompt = f"【元素】：{data.get('element_mapping')} 【场景】：{data.get('scene_description')} 【动作】：{data.get('shot_description')}\n需包含：位置、朝向、景别、光影。"
    if project_info: user_prompt += f"\n色彩：{project_info.get('visual_color_system','')}"
    
    res_start = ai_service.run_text_generation([{'role': 'system', 'content': sys + " (首帧)"}, {'role': 'user', 'content': user_prompt}], config)
    res_end = ai_service.run_text_generation([{'role': 'system', 'content': sys + " (尾帧)"}, {'role': 'user', 'content': user_prompt}], config)
    
    if res_start.get('success'):
        return jsonify({'success': True, 'prompt': res_start['content'], 'end_frame_prompt': res_end.get('content', '')})
    return jsonify({'success': False}), 500

@app.route('/api/generate/fusion_video', methods=['POST'])
def generate_fusion_video():
    data = request.json
    fusion_id = data.get('fusion_id')
    project_id = data.get('project_id')
    
    current_fusion = db.get_fusion(project_id, fusion_id)
    if not current_fusion: return jsonify({'success': False, 'error': 'Not found'}), 404
    
    s_url = current_fusion.get('result_image')
    e_url = current_fusion.get('end_frame_image')
    if not s_url: return jsonify({'success': False, 'error': 'No start image'}), 400
    
    s_path = os.path.abspath(os.path.join(STATIC_FOLDER, s_url.lstrip('/')))
    e_path = os.path.abspath(os.path.join(STATIC_FOLDER, e_url.lstrip('/'))) if e_url else None
    
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    
    result = ai_service.run_video_generation(
        current_fusion.get('fusion_prompt') or "high quality video",
        s_path, e_path, config, 
        os.path.join(STATIC_FOLDER, VIDEO_SAVE_DIR), 
        f"/{VIDEO_SAVE_DIR}"
    )
    
    if result.get('success'):
        db.update_fusion(project_id, fusion_id, {'video_url': result['url']})
        return jsonify({'success': True, 'url': result['url']})
    return jsonify({'success': False}), 500

if __name__ == '__main__':
    ensure_static_dirs()
    print(f"Server started on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)