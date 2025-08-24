# Docker 部署指南

## 快速开始

### 开发环境
```bash
# 构建并启动服务
docker-compose up

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 生产环境
```bash
# 使用生产配置（包含nginx反向代理）
docker-compose --profile production up -d
```

## 配置说明

### 环境变量
- `DATABASE_PATH`: 数据库文件路径（默认：`rss_reader.db`）
- `FLASK_ENV`: Flask环境（默认：`production`）

### 端口配置
- 开发环境：`http://localhost:5001`
- 生产环境：`http://localhost:80`

### 数据持久化
数据库文件存储在 `./data` 目录，确保数据不会丢失。

## Docker 命令

```bash
# 构建镜像
docker build -t rss-reader .

# 运行容器
docker run -p 5001:5001 -v $(pwd)/data:/app/data rss-reader

# 查看运行状态
docker ps

# 停止服务
docker-compose down

# 重新构建并启动
docker-compose up -d --build
```

## 生产环境建议

1. **域名配置**: 修改 `nginx.conf` 中的 `server_name`
2. **SSL证书**: 添加 HTTPS 支持
3. **日志管理**: 配置日志轮转
4. **监控**: 添加健康检查和监控
5. **备份**: 定期备份数据库文件