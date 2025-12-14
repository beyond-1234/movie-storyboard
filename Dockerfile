# Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装依赖 (建议先复制 requirements.txt 利用缓存)
COPY requirements.txt .
# 安装系统依赖 (opencv等可能需要)
RUN apt-get update && apt-get install -y libgl1-mesa-glx && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

# 创建必要的挂载点目录 (即使不挂载，保证目录存在)
RUN mkdir -p /app/logs /app/static /app/data

# 暴露端口
EXPOSE 5000

# 6. 设置环境变量
# 防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1
# 确保控制台输出直接打印，不被缓存
ENV PYTHONUNBUFFERED=1

# 7. 启动命令
# 使用 Gunicorn 启动，而不是 python app.py
# -w 4: 开启 4 个 worker 进程
# -b 0.0.0.0:5000: 绑定到所有 IP 的 5000 端口
# app:app : 第一个 app 指的是文件名 (app.py)，第二个 app 指的是 Flask 实例名
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]