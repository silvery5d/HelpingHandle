#!/bin/bash
# HelpingHandle 部署脚本
# 在 Google Compute Engine VM 上运行

set -e

DOMAIN=${1:?"用法: ./deploy.sh your-domain.com"}

echo "=== 1. 安装 Docker ==="
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER

echo "=== 2. 配置 Nginx 域名 ==="
sed -i "s/YOUR_DOMAIN.com/$DOMAIN/g" nginx/default.conf

echo "=== 3. 创建 .env 文件 ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 .env 文件，填入你的 ANTHROPIC_API_KEY："
    echo "  nano .env"
    echo "填好后重新运行此脚本"
    exit 1
fi

echo "=== 4. 首次启动（获取 SSL 证书前，先用 HTTP）==="
# 临时 nginx 配置（仅 HTTP，用于 certbot 验证）
cat > nginx/default.conf.tmp << TMPEOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
TMPEOF

cp nginx/default.conf nginx/default.conf.ssl
cp nginx/default.conf.tmp nginx/default.conf

docker compose up -d app nginx

echo "=== 5. 获取 SSL 证书 ==="
docker compose run --rm certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email admin@$DOMAIN \
    --agree-tos --no-eff-email \
    -d $DOMAIN

echo "=== 6. 切换到 HTTPS 配置 ==="
cp nginx/default.conf.ssl nginx/default.conf
rm nginx/default.conf.tmp nginx/default.conf.ssl
docker compose restart nginx

echo ""
echo "=== 部署完成！ ==="
echo "你的网站已上线: https://$DOMAIN"
echo ""
echo "常用命令："
echo "  docker compose logs -f        # 查看日志"
echo "  docker compose restart         # 重启服务"
echo "  docker compose down            # 停止服务"
echo "  docker compose up -d --build   # 重新构建并启动"
