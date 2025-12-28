# --- 第一阶段：构建 ---
FROM node:18-alpine as build-stage

WORKDIR /app

# 复制 package.json 并安装依赖
COPY package.json package-lock.json* ./
RUN npm install

# 复制源代码并构建
COPY . .
RUN npm run build

# --- 第二阶段：生产环境 ---
FROM nginx:alpine as production-stage

# 复制构建好的静态文件到 Nginx 目录
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 复制自定义的 Nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]