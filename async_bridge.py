from flask import json

def context_runner(app, target_route_func, request_data, save_callback=None):
    """
    通用上下文运行器 (已修复 Tuple 返回值解包问题)
    """
    # 1. 伪造请求上下文，注入 data
    with app.test_request_context(json=request_data):
        try:
            # 2. 调用原函数 (完全复用 main.py 逻辑)
            # 这里原本可能返回 Response 对象，也可能返回 (Response, status_code) 元组
            raw_response = target_route_func()
            
            # === 修复开始：处理 Flask 返回 tuple 的情况 ===
            if isinstance(raw_response, tuple):
                # 如果是元组 (response, status_code)，取第一个元素
                response_obj = raw_response[0]
            else:
                # 如果直接是 Response 对象
                response_obj = raw_response
            # === 修复结束 ===

            # 3. 解析结果
            # 现在 response_obj 肯定是 Flask 的 Response 对象了，可以调 get_json
            result = response_obj.get_json()
            
            # 4. 如果成功且有回调，执行回调
            if result and result.get('success'):
                if save_callback:
                    print(f"✅ [后台] 执行保存回调...")
                    save_callback(result)
            else:
                # 提取真实的错误信息 (比如 AuditSubmitIllegal)
                error_msg = 'Unknown Error'
                if result:
                    error_msg = result.get('error_msg') or result.get('error') or str(result)
                
                print(f"⚠️ [后台] 业务返回失败: {error_msg}")
                # 抛出这个具体的错误，这样 task_queue 就能捕获并在前端显示
                raise Exception(error_msg)
                
        except Exception as e:
            # 这里会捕获上面的 raise Exception，并记录到任务的 error 字段中
            print(f"❌ [后台] 执行异常: {str(e)}")
            raise e