# FE.5 三端适配 — 验证步骤

> 验收：三端跑通 + 可人工复述的验证步骤。自动化覆盖见 `tests/js/test_fe_adapters.mjs`。

## 1. Web 浏览器

1. `npm run dev` → 打开 `http://localhost:5173/`
2. 拖拽窗口宽度：
   - **≥1280** 三栏（导航 / 侧栏 / 内容），`data-bp="lg"`
   - **768–1279** 双栏，`data-bp="md"`
   - **<768** 单栏，`data-bp="sm"`
3. 地址栏 `#/tasks?filter=done` 可直接分享打开任务中心并带筛选
4. 「复制链接」（`shareUrl` + `copyText`）粘贴到新标签可恢复路由

## 2. 桌面 Win（Tauri）

1. `cd src-tauri && cargo run`（或 `tauri dev`）弹出窗口
2. 标题可随路由更新（`DesktopAdapter.setTitle`）
3. 最小化 / 托盘显隐（`minimize` / `setTrayVisible`；无托盘环境 mock 回落）
4. 快捷键：`CmdOrCtrl+K` 注册成功（`register_shortcut`）
5. 拖入 `.yaml`：`data-dragover="true"` 高亮 → `onFileDrop` 收到路径
6. 通知：`notify` 成功或 Web Notification 降级

## 3. 移动（Android / 平板 WebView 或窄窗）

1. 窄窗 <768 或真机打开 `http://<局域网 IP>:5173/`
2. 刘海/圆角屏：`--safe-*` 生效，内容不被状态栏/小白条遮挡
3. 点输入框：`html[data-kb="open"]`，底部 composer 与抽屉避让软键盘
4. 左右滑动手势：`swipe-left/right` 触发（GestureTracker，阈值 48px）
5. 系统返回：有历史则后退，否则回落 `#/chat`

## 自动化

```powershell
node --experimental-strip-types tests/js/test_fe_adapters.mjs
npm run test:ui
```
