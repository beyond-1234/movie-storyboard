# 1. 选择基础镜像
# 使用 slim 版本可以减小镜像体积，python:3.9-slim 是个不错的选择
FROM python:3.9-slim

# 2. 设置工作目录
# 容器内的所有后续命令都会在这个目录下执行
WORKDIR /app

# 3. 复制依赖文件并安装
# 先只复制 requirements.txt，利用 Docker 缓存机制。
# 只要 requirements.txt 不变，再次构建时这一步会直接使用缓存，速度极快。
COPY requirements.txt .

# 安装依赖，这里推荐使用清华源或阿里源加速
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制项目代码
# 将当前目录下的所有文件（除了 .dockerignore 排除的）复制到容器的 /app 目录
COPY . .

# 5. 暴露端口
# 告诉 Docker 这个容器将使用 5000 端口（Flask 默认端口）
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
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]