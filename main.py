import os
import time
import re
import uuid
import json
from typing import List, Optional, Dict, Any
from flask import Flask, request, jsonify, send_file

import ai_service 
from jianying_exporter import export_draft
from data_manager import DataManager
from media_manager import MediaManager

# --- 配置 ---
STATIC_FOLDER = "."
app = Flask(__name__, static_url_path='', static_folder=STATIC_FOLDER)

# 初始化管理器
db = DataManager() 
media_mgr = MediaManager(STATIC_FOLDER)

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
    # 支持通过 query param 过滤剧集
    series_id_filter = request.args.get('series_id')

    # 1. 获取项目列表
    if series_id_filter:
        # 如果指定了 series_id，只获取该剧集下的项目
        projects = db.get_projects_by_series(series_id_filter)
    else:
        # 否则获取全部项目
        projects = db.get_all_projects()
    
    # 2. 获取所有剧集并建立 ID -> Name 映射
    series_list = db.get_all_series()
    series_map = {s['id']: s['name'] for s in series_list}
    
    # 3. 注入剧集名称
    for p in projects:
        sid = p.get('series_id')
        if sid and sid in series_map:
            s_name = series_map[sid]
            p['series_name'] = s_name
            # 生成前端展示用的名称，格式：【剧集名】项目名
            p['display_name'] = f"【{s_name}】{p.get('film_name', '')}"
        else:
            p['series_name'] = ""
            p['display_name'] = p.get('film_name', '未命名项目')
            
    return jsonify(projects)

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
    
    # 传入 media_mgr 和 shot_id 作为 entity_id 进行版本管理
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
    shots = db.get_shots(project_id)
    # 导出模块可能还需要适配，暂维持原样，假设导出目录已由 MediaManager 创建
    result = export_draft(project_info, shots, STATIC_FOLDER, "exports")
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
    character_id = data.get('character_id') # 获取 ID 用于版本控制
    
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
    
    # 使用 MediaManager 上传，并启用版本管理
    url, err = media_mgr.save_uploaded_file(request.files['file'], media_type='image', entity_id=cid)
    
    if err: return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True, 'url': url})

@app.route('/api/upload/scene_image', methods=['POST'])
def upload_scene_image():
    if 'file' not in request.files: return jsonify({'success': False, 'error': 'No file'}), 400
    sid = request.form.get('scene_id') or 'scene'
    
    # 使用 MediaManager 上传
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
    
    # scene_image 可能没有 strict 的 entity_id, 可选
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
    
    # 元素图，可能有 element_id
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
        entity_id=fusion_id # 使用 fusion_id 进行版本控制
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
    
    s_path = media_mgr.get_absolute_path(s_url)
    e_path = media_mgr.get_absolute_path(e_url) if e_url else None
    
    config = db.get_provider_config(data.get('provider_id'))
    if data.get('model_name'): config['model_name'] = data.get('model_name')
    result = ai_service.run_video_generation(
        current_fusion.get('fusion_prompt') or "high quality video",
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
    # 1. 收集项目下所有的实体 ID
    entity_map = {}
    
    # A. 获取角色
    chars = db.get_characters(project_id)
    for c in chars:
        entity_map[c['id']] = {'name': f"角色: {c['name']}", 'type': 'character'}
        
    # B. 获取分镜 (场景图通常绑定在分镜ID上)
    shots = db.get_shots(project_id)
    for s in shots:
        name = f"场{s.get('scene','?')}-镜{s.get('shot_number','?')}"
        entity_map[s['id']] = {'name': name, 'type': 'shot'}
        
    # C. 获取融图任务
    fusions = db.get_fusions(project_id)
    for f in fusions:
        # 融图任务ID通常用于存结果图、视频
        name = f"融图: 场{f.get('scene','?')}-镜{f.get('shot_number','?')}"
        entity_map[f['id']] = {'name': name, 'type': 'fusion'}
        
        # 融图任务下的元素 (Element) 也有独立的图片
        if f.get('elements'):
            for el in f['elements']:
                if el.get('id'):
                    entity_map[el['id']] = {'name': f"元素: {el.get('name')} ({name})", 'type': 'element'}

    # 2. 扫描文件系统
    history_list = media_mgr.scan_project_files(entity_map)
    print(history_list)
    return jsonify(history_list)

@app.route('/api/generate/analyze_image', methods=['POST'])
def analyze_uploaded_image():
    # 1. 检查文件
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    # 2. 保存文件
    temp_id = f"analysis_{uuid.uuid4().hex[:8]}"
    url, err = media_mgr.save_uploaded_file(file, media_type='image', entity_id=temp_id)
    if err: return jsonify({'success': False, 'error': err}), 500
    
    image_abs_path = media_mgr.get_absolute_path(url)

    VISUAL_STYLE_PROMPT = """
    请作为一个专业的电影美术指导与摄影指导分析这张图片。
    请忽略图片中的具体剧情内容，重点提取画面的【视觉风格要素】，以便我将其作为Prompt输入给AI绘画工具来复制这种风格。

    请严格按照以下维度进行提取和描述：
    1. **艺术风格/流派** (Art Style): 如赛博朋克、吉卜力风格、诺兰电影感、80年代复古胶片等。
    2. **光影与氛围** (Lighting & Atmosphere): 如伦勃朗光、霓虹漫射、体积光(丁达尔效应)、高对比度黑白等。
    3. **色彩体系** (Color Palette): 如青橙色调、低饱和度莫兰迪色、高饱和度波普色等。
    4. **材质与渲染质感** (Texture & Rendering): 如胶片颗粒感、8K超高清、虚幻引擎5渲染等。

    最后，请将上述分析汇总为一段连贯的、高质量的中文Prompt描述（不需要分点，直接输出一段描述文本）。
    """

    # 3. 获取配置
    config = None
    settings = db.get_settings()
    for p in settings.get('providers', []):
        if p.get('type') == 'aliyun' and p.get('enabled', True):
            config = p
            break
    
    if not config:
        return jsonify({'success': False, 'error': 'No Aliyun provider configuration found.'}), 400
    
    # 4. 调用 AI Service (传入 image_path, PROMPT, config)
    result = ai_service.run_visual_analysis(image_abs_path, VISUAL_STYLE_PROMPT, config, media_mgr)
    
    # 5. 返回结果
    if result.get('success'):
        return jsonify({
            'success': True, 
            'style_description': result['content'],
            'image_url': url
        })
    else:
        return jsonify(result), 500

if __name__ == '__main__':
    print(f"Server started on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)