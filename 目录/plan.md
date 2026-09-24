# plan.md 鈥?杩涘害鏃ュ織

## [2026-09-24][FE.0] 闇€姹傜‘璁や笌鏂规閿佸畾

- 鐘舵€侊細鉁?瀹屾垚
- 鍐崇瓥閿佸畾锛堢敤鎴风‘璁わ級锛?
  1. 鍔熻兘锛氬璇?浠诲姟/鏂囦欢/LLM/MCP/DSL 鍏ㄩ潰鎵撶（
  2. 涓夌锛歐in + Web 浼樺厛
  3. 椋庢牸锛氭殩鐧芥瘺鐜荤拑 + 鏆栨潖/铚滄/闄跺湡 + 榧犲熬鑽夌豢 + 鎶€鑳芥爲/鎴愬氨鍖?
  4. 浜や簰锛歐S + REST + Tauri IPC锛圗ventBus锛?
  5. 鎬ц兘锛欶E.6 寤跺悗
- 鍙樻洿鏂囦欢锛歚鐩綍/鍓嶇浼樺寲瑙勫垝.md`锛堥攣瀹?5 椤?+ 璁捐涓诲紶 + 椤甸潰/閫夊瀷锛?
- 楠屾敹锛歔x] 5 椤瑰潎鏈夌敤鎴锋槑纭€夋嫨 [x] 璁捐涓诲紶鍙寚瀵?Token
- 涓嬩竴 Task锛欶E.1 妗嗘灦鎼缓

## [2026-09-24][FE.1] 鍓嶇妗嗘灦鎼缓

- 鐘舵€侊細鉁?瀹屾垚
- 鍙樻洿鏂囦欢锛?
  - `src/api/index.ts` 鈥?缁熶竴閫氫俊闂ㄩ潰锛圧EST/涓婁紶/骞冲彴 refresh锛?
  - `src/hooks/use-router.ts` + `use-react-hooks.ts` + `index.ts` 鈥?杞婚噺 hash 璺敱涓?React hooks
  - `src/stores/ui-store.ts` + `index.ts` 鈥?UI/璺敱鐘舵€侊紝鍏煎鏃㈡湁 session/tasks/agents
  - `src/features/index.ts` 鈥?涓氬姟鍩熻仛鍚?+ FEATURES 鍏冩暟鎹紙鎶€鑳芥爲锛?
  - `src/components/index.ts` 鈥?UI 绫诲悕濂戠害锛團E.4 鍏呭疄锛?
  - `src/styles/tokens.css` + `index.css` 鈥?鏆栬壊姣涚幓鐠?Token 闆忓舰
  - `src/services/index.ts` 鈥?`createServiceLayer` 鏀寔 `uploadFetch` 娉ㄥ叆
  - `src/App.tsx` 鈥?鎺ョ嚎 McpPanel锛涗慨澶?`llmDraft.providerId` 绫诲瀷
  - `src/hub/ws-client.ts` 鈥?`intentionalClose` 鏆撮湶涓诲姩鍏抽棴璇箟
  - `src/main.tsx` / `tsconfig.json` / `package.json` 鈥?鏍峰紡鍏ュ彛銆佷弗鏍?TS銆佹祴璇曠撼鍏?
  - `tests/js/test_fe_framework.mjs` 鈥?璺敱/闂ㄩ潰/UI Store/濂戠害鍗曟祴
- 楠屾敹缁撴灉锛?
  - [x] 閫氫俊灞傚崟娴?`test_fe_framework: ALL PASS`
  - [x] `npm run test:ui` 鍏ㄧ豢锛沗npm run test:py` 296 OK
  - [x] `npx tsc --noEmit` 閫氳繃锛坰trict + noUnusedLocals锛?
  - [x] `npm run build` 鎴愬姛锛圵eb 鍙瀯寤哄惎鍔級
- 閬楃暀锛?
  - Android/骞虫澘浠嶆寜瑙勫垝寤跺悗锛圱auri 绉诲姩鎵撳寘锛?
  - App 灏氭湭鎸?hash 璺敱鍒嗛〉闈紙FE.3 椤甸潰鍖栵級锛涘綋鍓嶄负鍗曢〉鑱氬悎
  - 缁勪欢搴撲粎绫诲悕濂戠害锛團E.4锛夛紱鎬ц兘 FE.6 寤跺悗

## [2026-09-24][FE.2] 璁捐绯荤粺 Token

- 鐘舵€侊細鉁?瀹屾垚
- 鍙樻洿鏂囦欢锛?
  - `src/styles/tokens.css` 鈥?primitive / semantic / component 涓夊眰锛涙殩鍏夐粯璁?+ 鏆栧 `data-theme`
  - `src/styles/tokens.ts` 鈥?绫诲瀷鍖栧鍑猴紙涓婚銆佹妧鑳芥爲銆丆SS 鍙橀噺鍚嶏級
  - `src/styles/base.css` / `components.css` 鈥?瀛椾綋灞傜骇钀藉湴 + 鎸夐挳/杈撳叆/鍗＄墖/Toast/鎶€鑳芥爲绫?
  - `src/styles/README.md` 鈥?Token 鏂囨。锛堝垎灞傘€佽涔夎壊銆佸昂搴︺€佺敤娉曪級
  - `src/styles/index.css` 鈥?鏍峰紡鍏ュ彛涓茶仈
  - `tests/js/test_design_tokens.mjs` 鈥?Token 楠屾敹娴嬭瘯
- 楠屾敹缁撴灉锛?
  - [x] 鑹叉澘 / 闂磋窛 / 鍦嗚 / 闃村奖 / 瀛椾綋灞傜骇锛圕SS 鍙橀噺锛?
  - [x] 鏂囨。璇存槑 `src/styles/README.md`
  - [x] `test_design_tokens: ALL PASS`
- 閬楃暀锛?
  - 鍘嗗彶 `src/styles.css` 浠嶆湁灏戦噺纭紪鐮佽壊锛孎E.3/FE.4 閫愭鏇挎崲
  - 鏆栧涓婚闇€鐪熸満/娴忚鍣ㄤ汉宸ョ湅涓€鐪煎姣斿害

## [2026-09-24][FIX] 绀轰緥 DeepSeek + 淇濆瓨缂?API Key 鏄庢枃

- 鐘舵€侊細鉁?瀹屾垚
- 鏍瑰洜锛歚onSave` 鏈啓鍏?`apiKeyPlain`锛屼繚瀛樺悗銆屾媺鍙栨ā鍨嬨€嶄粛璁や负鏈〉鏃?Key
- 鍙樻洿锛歚App.tsx` 淇濆瓨/鍚堝苟淇濈暀鏄庢枃 Key锛涢潰鏉夸笌鎶ラ敊绀轰緥鏀逛负 `https://api.deepseek.com/v1`
- 楠屾敹锛?/4 鍥炲綊 + 283 Python OK


## [2026-09-24][N11] OAuth 閴存潈

- 鐘舵€侊細鉁?瀹屾垚
- 鍙樻洿鏂囦欢锛?
  - `auth/oauth.py` 鈥?OAuthService锛歩ssue_tokens / verify_access / refresh锛堣疆鎹級/ revoke
  - `api/auth_routes.py` 鈥?`/api/auth/token` 路 `/refresh` 路 `/revoke` 路 `/whoami`
  - `tests/test_oauth.py` 鈥?13 涓崟娴?
- 楠屾敹缁撴灉锛?
  - [x] 鏈巿鏉冭澶囨棤娉曟敞鍐岋紙鏃?token / 浼€?/ 杩囨湡 鈫?AuthError锛?
  - [x] token 杩囨湡鍙画鏈燂紙refresh 鎹㈡柊 access锛屾棫 refresh 鍚婇攢杞崲锛?
  - [x] 娴嬭瘯 13/13 OK锛涘叏閲?296 OK
- 閬楃暀闂锛?
  - **鍐崇瓥**锛氭爣鍑嗗簱 HS256 椋庢牸 JWT锛堥潪瀹屾暣 OAuth2 IdP锛夛紱璁惧 `client_credentials` 璇箟
  - **鍐崇瓥**锛歐S 娉ㄥ唽榛樿浠嶅吋瀹?HMAC锛沗allow_register` 渚涘己鍒?OAuth 妯″紡鎺ュ叆
  - secret 鏉ヨ嚜 `LOOM_AUTH_SECRET`


## [2026-09-24][N12] 宸ョ▼鍖栵紙CI / lint / 涓€閿叏閲忔祴璇曪級

- 鐘舵€侊細鉁?瀹屾垚
- 鍙樻洿鏂囦欢锛?
  - `scripts/test_all.py` 鈥?涓€閿窇 Python unittest + 鍏ㄩ儴 JS + Rust cargo test
  - `scripts/lint_all.py` 鈥?py_compile +锛堝彲閫?ruff锛? cargo fmt --check
  - `.github/workflows/ci.yml` 鈥?鐭╅樀 CI锛坧ython/js/rust + lint锛夛紝绾㈢伅鍗冲け璐?
  - `ruff.toml` / `requirements.txt` / `package.json` scripts锛坱est/lint/ci锛?
- 楠屾敹缁撴灉锛?
  - [x] 涓€鏉″懡浠わ細`npm run test` / `python scripts/test_all.py`
  - [x] CI 宸ヤ綔娴佸け璐ュ嵆绾?
  - [x] lint锛歅ython 璇硶 + Rust fmt 閫氳繃
- 閬楃暀锛歳uff 鏈満鏈锛坙int 鍥為€€ py_compile锛夛紱CI 鐢?GitHub Actions


## [2026-09-24][STACK] 鎶€鏈爤鍖归厤涓庝紭鍖?

- 鐘舵€侊細鉁?瀹屾垚
- 鐩爣鏍堝鐓э細
  | 鏍?| 鐘舵€?|
  |----|------|
  | Shell: Tauri 2.0 + React + TS + Vite | 鉁?宸插叿澶?|
  | Hub: Python 3.11+ + FastAPI + Uvicorn + LangGraph + Pydantic | 鉁?宸插叿澶?|
  | DSL: YAML + PyYAML + JSON Schema + jsonschema | 鉁?schema 浼樺厛 jsonschema锛屽洖閫€鍐呯疆 |
  | Agent: MCP SDK + httpx | 鉁?httpx锛沵cp 鍏?requirements锛堝綋鍓嶄负鍏煎 JSON-RPC 浼犺緭锛?|
  | Device: WebSocket + HMAC-SHA256 | 鉁?宸插叿澶?|
  | Store: SQLite | 鉁?sync/engine |
  | Deploy: Docker + GitHub Releases | 鉁?Dockerfile / compose / release.yml |
  | Tools: Ruff + pytest + pytest-asyncio | 鉁?pyproject + lint/test 鍒囨崲 pytest/ruff |
- 鍙樻洿鏂囦欢锛?
  - `requirements.txt` / `pyproject.toml`锛坧ytest + ruff 閰嶇疆锛?
  - `dsl/schema.py` 鈥?jsonschema Draft202012 浼樺厛锛宐uiltin 鍥為€€锛沗backend_name()`
  - `Dockerfile` / `docker-compose.yml`
  - `.github/workflows/release.yml`锛坱ag 瑙﹀彂锛氭祴璇曗啋Docker鈫掍笂浼?app.html锛?
  - `scripts/lint_all.py` / `test_all.py` / `ci.yml` 瀵归綈 ruff + pytest
- 楠屾敹锛?
  - [x] pytest 296 passed锛泃est_all Py+JS+Rust ALL PASS
  - [x] schema backend=jsonschema锛堝凡瀹夎锛?
  - [x] Docker / GitHub Releases 閰嶇疆灏辩华


## [2026-09-24][STACK] 鎶€鏈爤鍖归厤涓庝紭鍖?

- 鐘舵€侊細鉁?瀹屾垚
- 鐩爣鏍堝鐓э細
  | 鏍?| 鐘舵€?|
  |----|------|
  | Shell: Tauri 2.0 + React + TS + Vite | 鉁?宸插叿澶?|
  | Hub: Python 3.11+ + FastAPI + Uvicorn + LangGraph + Pydantic | 鉁?宸插叿澶?|
  | DSL: YAML + PyYAML + JSON Schema + jsonschema | 鉁?schema 浼樺厛 jsonschema锛?.26锛夛紝builtin 鍥為€€ |
  | Agent: MCP SDK + httpx | 鉁?httpx锛沵cp 鍏?requirements锛堝綋鍓嶄负鍏煎 JSON-RPC 浼犺緭锛?|
  | Device: WebSocket + HMAC-SHA256 | 鉁?宸插叿澶?|
  | Store: SQLite | 鉁?sync/engine |
  | Deploy: Docker + GitHub Releases | 鉁?Dockerfile / compose / release.yml |
  | Tools: Ruff + pytest + pytest-asyncio | 鉁?pyproject + lint/test 鍒囨崲 pytest/ruff |
- 鍙樻洿鏂囦欢锛?
  - `requirements.txt` / `pyproject.toml`锛坧ytest-asyncio auto + ruff 閰嶇疆锛?
  - `dsl/schema.py` 鈥?jsonschema Draft202012 浼樺厛锛涢敊璇枃妗堟槧灏勪腑鏂囷紱`backend_name()`
  - `Dockerfile` / `docker-compose.yml` / `.github/workflows/release.yml`
  - `scripts/lint_all.py` / `test_all.py` / `ci.yml` 瀵归綈 ruff + pytest
- 楠屾敹锛?
  - [x] pytest 鍏ㄧ豢锛堝惈 schema 涓枃鏂囨鏂█锛?
  - [x] test_all Py+JS+Rust ALL PASS
  - [x] schema backend=jsonschema
  - [x] Docker / GitHub Releases 閰嶇疆灏辩华
- 閬楃暀锛歁CP SDK 宸插叆渚濊禆锛屼紶杈撳眰浠嶄负鍏煎 JSON-RPC锛堝彲鍒囨崲瀹樻柟 mcp锛夛紱ruff 鍙?`pip install ruff`


## [2026-09-24][浜ゆ帴] 涓婁笅鏂囧帇缂?+ 鍓嶇浼樺寲瑙勫垝

- 鐘舵€侊細鉁?鏂囨。瀹屾垚锛堢紪鐮佸緟纭锛?
- 鍙樻洿鏂囦欢锛坄鐩綍/`锛夛細
  - `浜ゆ帴鎵嬪唽.md` 鈥?鍏ㄩ噺宸ヤ綔鍘嬬缉銆佷唬鐮佸湴鍥俱€佸喅绛栥€佸懡浠ゃ€侀仐鐣?
  - `椤圭洰浠嬬粛.md` 鈥?瀹氫綅 / 鍔熻兘 / 浣跨敤璇存槑锛堥噸鍐欙級
  - `鍓嶇浼樺寲瑙勫垝.md` 鈥?FE.0鈥揊E.7 璁″垝 + 5 椤瑰緟纭
- ROADMAP锛氭柊澧炪€孭6 路 鍓嶇鐢熶骇鍖栵紙FE锛夈€?
- 寰呯敤鎴风‘璁?5 椤瑰悗鍚姩 FE.1 妗嗘灦鎼缓

## [2026-09-24][FE.3] 鏍稿績椤甸潰锛堝璇濆伐浣滃彴 / 浠诲姟涓績 / 璁剧疆锛?
- 鐘舵€侊細鉁?瀹屾垚
- 鍙樻洿鏂囦欢锛?  - `src/features/page-states.ts` 鈥?Loading / Empty / Error / PageShell + phaseOf
  - `src/features/chat-workbench.ts` 鈥?瀵硅瘽宸ヤ綔鍙帮紙鍔犺浇/绌?閿欒/灏辩华 + 鍙戦€?disabled锛?  - `src/features/task-center.ts` 鈥?浠诲姟涓績 + ResultCard锛堢瓫閫?+ 鍥涙€侊級
  - `src/features/settings-page.ts` 鈥?璁剧疆锛圠LM / MCP 瀛愰〉 + 绌烘€侊級
  - `src/features/index.ts` 鈥?椤甸潰瀵煎嚭
  - `src/styles/pages.css` + `index.css` 鈥?椤靛３涓庣姸鎬佹牱寮?  - `src/App.tsx` 鈥?hash 璺敱鎺ョ嚎锛坈hat / tasks / settings锛?  - `tests/js/test_fe_pages.mjs` 鈥?涓夐〉 + 鍥涙€侀獙鏀?- 楠屾敹缁撴灉锛?  - [x] 瀵硅瘽宸ヤ綔鍙?/ 浠诲姟涓績 / 璁剧疆 涓夐〉
  - [x] 鍔犺浇 / 绌?/ 閿欒鐘舵€佸畬鏁达紙hover/disabled 鐢辩粍浠跺眰鎵挎帴锛?  - [x] `test_fe_pages: ALL PASS` + `npm run test:ui` 鍏ㄧ豢 + `tsc` 閫氳繃
- 閬楃暀锛?  - App 涓嬫柟浠嶄繚鐣欐棫 Workspace 鎬昏锛堝吋瀹规棫娴嬭瘯锛孎E.4 鍙敹鏁涳級
  - 璁剧疆椤?hover 缁嗚妭涓?FE.4 閫氱敤缁勪欢涓€骞舵墦纾?
## [2026-09-24][FE.4] 閫氱敤缁勪欢

- 鐘舵€侊細鉁?瀹屾垚
- 鍙樻洿鏂囦欢锛?  - `src/components/index.ts` 鈥?Button / Input / Modal / Toast / Layout / Card + ComponentGallery 绀轰緥
  - `src/styles/components.css` 鈥?鐘舵€佹牱寮忥紙disabled/loading/invalid/open/tone锛?  - `tests/js/test_fe_components.mjs` 鈥?鐘舵€侀綈鍏?路 鍙鐢?路 鏈夌ず渚?- 楠屾敹缁撴灉锛?  - [x] Button / Input / Modal / Toast / Layout锛? Card锛?  - [x] 鐘舵€侀綈鍏細disabled / loading / invalid / open / tone success|error / density
  - [x] 鍙鐢?+ `ComponentGallery` 绀轰緥
  - [x] `test_fe_components: ALL PASS` + `npm run test:ui` 鍏ㄧ豢 + `tsc` 閫氳繃
- 閬楃暀锛欰pp 鍐呭彲閫愭鏀圭敤鏂扮粍浠舵浛鎹㈠瓧绗︿覆绫诲悕锛團E.5/鍚庣画锛?

## [2026-09-24][FE.5] 三端适配

- 状态：✅ 完成
- 变更文件：
  - `src/platform/adapters.ts` — Host/断点/安全区/手势/软键盘/返回键/桌面 DesktopAdapter/路由分享
  - `src/platform/index.ts` — PlatformLayer 扩展 host/breakpoint/desktop
  - `src/styles/adapters.css` + `index.css` — 安全区、断点列、底部抽屉、软键盘避让、拖拽高亮
  - `目录/FE5_三端验证步骤.md` — Web / Win / 移动人工验证步骤
  - `tests/js/test_fe_adapters.mjs` — 三端适配验收
- 验收结果：
  - [x] 桌面：标题/最小化/托盘/快捷键/拖拽/通知（Tauri mock + Web Notification 降级）
  - [x] 移动：安全区 / 手势 / 软键盘 / 返回键
  - [x] Web：断点 lg|md|sm + hash 路由分享
  - [x] `test_fe_adapters: ALL PASS` + `npm run test:ui` 全绿 + `tsc` 通过 + Python 296 OK
  - [x] 验证步骤文档：`目录/FE5_三端验证步骤.md`
- 遗留：真机 `cargo run` / Android 打包仍需人工按验证步骤点一遍；Tauri 侧 set_window_title 等命令为对齐约定（`# 需确认当前版本API`）

## [2026-09-24][FE.6] 性能优化（用户本轮启动，覆盖此前延后）

- 状态：✅ 完成
- 变更文件：
  - `src/perf/index.ts` — computeWindow / VirtualList / memo / shallowEqual / debounce / useEvent
  - `src/features/task-center.ts` — ResultCard memo + >20 条走 VirtualList
  - `src/features/chat-workbench.ts` — MessageRow memo
  - `vite.config.ts` — cssCodeSplit / manualChunks react-vendor / es2022
  - `tests/js/test_fe_perf.mjs` — 窗口裁剪 / memo / 防抖 / 构建拆包
- 验收结果：
  - [x] 懒加载与代码分割：react-vendor 拆包 + cssCodeSplit（`npm run build` 通过）
  - [x] 虚拟列表：100 条仅渲染窗口内节点
  - [x] memo：ResultCard / MessageRow
  - [x] 资源优化：sourcemap 关闭、chunk 警告阈值、vendor 拆分
  - [x] `test_fe_perf: ALL PASS` + `npm run test:ui` 全绿 + `tsc` 通过 + Python 296 OK
- 遗留：路由级 React.lazy 可在 FE.7 收敛 App 时再做；未设 Lighthouse 硬指标（仍按 FE.0）

## [2026-09-24][FE.7] 交付

- 状态：✅ 完成
- 变更文件：
  - `目录/FE7_交付清单.md` — 交付物 / 三端启动命令 / 开发 / 构建部署 / 验证清单
  - `README.md` — 架构 + 开发 + 构建部署（公开首页，标注开发中）
- 验收结果：
  - [x] README 含架构 / 开发 / 构建部署
  - [x] 三端启动命令 + 验证步骤（清单 §2 §5 + FE5 文档）
  - [x] 交付清单齐全
  - [x] `npm run test:ui` 全绿 · `test:py` 296 OK · `tsc` / `lint` / `build` 通过
- 遗留：人工三端点验未勾选（清单 §5 空项）；移动端正式打包未做