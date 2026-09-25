# INSTALL.md — Loom 10 分钟上手

> 目标：陌生人按本文从零跑起 **Web + Hub**（Windows 优先）。  
> 密钥见 [SECURITY.md](./SECURITY.md) · 运维见 [RUNBOOK.md](./RUNBOOK.md)

---

## 0. 环境要求

| 组件 | 版本 | 检查 |
|------|------|------|
| Node.js | 20+ | `node -v` |
| Python | 3.11+ | `python -V` |
| （可选）Docker | 24+ | `docker -v` |
| （可选）Rust + WebView2 | 桌面 Win 壳 | `cargo -V` |

---

## 1. 获取代码

```powershell
git clone https://github.com/Yixi233-mo/Loom.git
cd Loom
```

## 2. 安装依赖（约 2 分钟）

```powershell
npm install
pip install -r requirements.txt
```

## 3. 配置密钥（约 1 分钟）

```powershell
Copy-Item .env.example .env
# 用记事本改 .env：至少设置 WS_SECRET / LOOM_AUTH_SECRET / LOOM_MASTER_KEY
```

开发可先用默认值（Hub 会告警）；**生产必须改强口令**（见 SECURITY.md）。

## 4. 启动（约 30 秒）

```powershell
# 推荐：Hub + 前端
npm run start
# 浏览器打开 http://127.0.0.1:5173
```

健康检查：

```powershell
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/ready
```

## 5. 可选方式

### Docker Hub

```powershell
$env:WS_SECRET="随机强口令"; $env:LOOM_AUTH_SECRET="..."; $env:LOOM_MASTER_KEY="..."
docker compose up -d hub
# 镜像固定 tag：loom/hub:0.1.0（不要用 latest）
```

数据在 `./data`，插件在 `./plugins`，`down/up` 不丢。

### Windows 安装包

```powershell
npm run build:windows
# 产物 dist-bundle/*.msi 或 *-setup.exe，双击安装
```

### 单文件预览（无 Hub）

```powershell
npm run build:single   # 打开 app.html
```

## 6. 常见问题

| 现象 | 处理 |
|------|------|
| 8765 被占用 | 改 `WS_PORT` 后重启 Hub |
| 浏览器跨域失败 | 用 `npm run start`（Vite 已代理 `/api`） |
| `/ready` 503 | 看响应 `checks`：secrets / model / database |
| 依赖未就绪 | 见启动日志「依赖未就绪」清单 |

## 7. 验收清单（10 分钟内）

- [ ] `npm run start` 无报错  
- [ ] 浏览器能打开工作台  
- [ ] `/health` 200 · `/ready` 200  
- [ ] 对话页可发消息（未配模型时为本地回声）  

**完成。** 更细的验证步骤见 `目录/07-交付验收/`。
