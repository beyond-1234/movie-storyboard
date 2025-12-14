# async_bridge.py
from flask import json

def context_runner(app, target_route_func, request_data, save_callback=None):
    """
    通用上下文运行器 (完全不包含业务逻辑)
    
    :param app: Flask app 实例
    :param target_route_func: main.py 中原本的视图函数 (如 generate_fusion_image)
    :param request_data: 前端传来的 JSON 数据 (dict)
    :param save_callback: 一个函数，接受 API 返回的 result (dict)，负责具体的保存逻辑
    """
    # 1. 伪造请求上下文，注入 data
    with app.test_request_context(json=request_data):
        try:
            # 2. 调用原函数 (完全复用 main.py 逻辑)
            response = target_route_func()
            
            # 3. 解析结果
            result = response.get_json()
            
            # 4. 如果成功且有回调，执行回调
            if result and result.get('success'):
                if save_callback:
                    print(f"✅ [后台] 执行保存回调...")
                    save_callback(result)
            else:
                error = result.get('error_msg', 'Unknown Error') if result else 'No result'
                raise Exception(error)
                
        except Exception as e:
            print(f"❌ [后台] 执行异常: {str(e)}")
            raise e