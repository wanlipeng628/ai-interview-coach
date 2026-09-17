# ---------- 构建阶段 ----------
FROM node:20-alpine AS build

WORKDIR /app

# 限制 Node 构建时的堆内存，避免小内存服务器构建阶段被 OOM
ENV NODE_OPTIONS=--max-old-space-size=512

COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm ci

COPY . .
RUN npm run build

# ---------- 运行阶段 ----------
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
