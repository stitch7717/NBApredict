# NBA 预测系统 — 开发指南

## 防复发红线（历史重复错误，详见 resolve.md 14.8）

1. **动库前必 mysqldump**（曾两次误删 game_record）
2. **新数据源先测匹配率再入库**（队名映射问题已踩 2 轮，用 `team_id_of()` 并断言 30 队全匹配）
3. **抓取后做数量断言**（每赛季场次 vs 预期；静默失败曾导致 2016-17 只入库 388 场）
4. **禁止新硬编码**（赛季用 constants 的 SEASONS/CURRENT_SEASON；曾散落 5 处 '2025-26'）
5. **新 ID 先定命名空间**（球员=NBA PERSON_ID、bbref 球员=bbref_ 前缀、比赛=espn_ 前缀，禁止混用）

## 项目结构

```
nba-predict-algorithm/   Python FastAPI (localhost:8000)
nba-predict-backend/     Java SpringBoot (localhost:8080, context-path: /api)
nba-predict-frontend/    Vue3 + Vite (localhost:3000)
nba-predict-sql/         MySQL 初始化脚本
```

## 启动顺序

1. MySQL (nba_predict 库)
2. `cd nba-predict-algorithm && python main.py`
3. `cd nba-predict-backend && mvn clean package -DskipTests && java -jar target/nba-predict-backend-1.0.0.jar`
4. `cd nba-predict-frontend && npm run dev`

**开发环境注意**：
- Python uvicorn StatReload 在 Windows 下**不可靠**（改了代码不重载）——改 Python 后直接重启服务，并用 `curl localhost:8000/...` 验证新字段存在
- 前端改完先 `npm run build` 验证编译，再刷新浏览器；行为异常且 build 通过 → 先重启 dev server（HMR 缓存）

## 核心技术约束

### 字段命名：三层不一致是最大坑

```
Python (SQLAlchemy) → snake_case:  player_name, points_per_game
Java (Jackson/Map)   → 原样透传:     player_name, points_per_game
Vue (JavaScript)     → camelCase:   playerName, pointsPerGame
```

**规则**：
- Python API 响应：保持 snake_case，不做转换
- Java 层：如果直接透传 Map，key 保持 snake_case  
- Vue 前端：**始终用 `??` 降级** `(val.camelCase ?? val.snake_case ?? default)`
- 新建 API 响应字段时，前端两个命名都支持

### HTTP 代理架构

```
Vite DevServer (:3000)
├── /api/*       → Java 后端  (:8080)   # request.js (baseURL: /api)
├── /data/*      → Python     (:8000)   # pythonRequest (baseURL: '')
└── /algorithm/* → Python     (:8000)   # pythonRequest (baseURL: '')
```

**规则**：
- 调用 Java API → 用 `request`（`@/api/request` default export）
- 调用 Python API → 用 `pythonRequest`（`@/api/request` named export）
- 不要混用

### Controller 层

- POST 接口用 `@RequestBody` + DTO record，绝不用 `@RequestParam`
- 不要在 Controller 类上加 `@Validated`（会导致 AOP 代理冲突 NPE）
- 分页参数校验手动做，不用注解
- **预测必须自动落库**：`TeamServiceImpl.predict()` / `PlayerServiceImpl.predict()` 成功后插入 `predict_record`（status=PREDICTED），改预测链路不要破坏此行为；校准走 `/record/calibrate`（回填真实值 → 算误差 → CALIBRATED）

### 前端

- `const fn = () => {...}` 定义在 `ref()` / `reactive()` 之前（避免 TDZ）。连锁症状：`Cannot read properties of null (reading 'parentNode')` 是 TDZ 崩溃的下游错误，根因看 Console 第一条 `Cannot access ... before initialization`
- 新页面组件放 `src/views/<name>/index.vue`
- 图标用全局注册的 Element Plus Icons 字符串名
- API 调用加 `try/catch`，catch 里至少 `console.error`
- 页面根容器：`max-width` 必须搭配 `margin: 0 auto`（居中）
- **新建 store / 路由文件后必须重启 Vite dev server**（HMR 对新文件挂载不可靠，表现：build 通过但页面行为是旧的）

### 双角色权限

- Pinia `stores/user.js`（role: null | 'guest' | 'admin'，localStorage 持久化，无密码）
- 路由守卫在 `router/index.js`：未选身份 → `/entry`；guest 访问 `ADMIN_ROUTES`（/settings /odds /record）→ 跳首页
- 守卫直接读 `localStorage.getItem('nba-predict-role')`，**不要**在 router 里 `useUserStore()`（循环依赖）
- MainLayout 菜单按角色过滤；新增管理页要同时加进 `adminMenuItems` 和 `ADMIN_ROUTES`
- 已删除页面：系列赛（series）、数据看板（dashboard）——不要引用

### 系数体系现状（v2 后）

- 系统设置页**只有赔率融合权重（odds_weight）是活的**（预测时从 DB 读）
- 其他系数（all_star/veteran/injury/clutch/home/fatigue）是 `settings.py` 静态值，由 `scripts/tune_coefficients.py` 回测调优——**不要再往设置页加系数滑块，它们不会生效**
- 球员预测读 `COEFFICIENT_CONFIG` 静态值；球队预测是 Ridge 模型 + 胜率从分差推导（`1/(1+e^(-diff/7))`），不走系数链

### 球队队标

- 30 支球队官方 SVG 队标存于 `src/assets/team-logos/`（按缩写命名，如 `LAL.svg`）
- 全局组件 `<TeamLogo :abbr="缩写" :size="32" />` 已在 main.js 注册，任何页面可直接使用，加载失败自动显示缩写圆形徽章兜底
- API 只返回队名时，用 `teamAbbrOf(队名)`（`@/constants/teams`）解析缩写，支持中英文名
- 队标+队名组合布局用全局类 `.team-cell`，对阵 vs 分隔符用 `.matchup-vs`

## 数据源（2026-08 变更：stats.nba.com 已封锁）

**stats.nba.com 官方 API 已被 Akamai 完全封锁**（2026 年新增 OAUTH2 认证 + 浏览器指纹检测，nba_api 库、cookie 复用、浏览器 fetch 均被拒）。现行数据源：

| 数据 | 来源 | 脚本 |
|------|------|------|
| 比赛记录（10 赛季） | ESPN site API（scoreboard 按月区间，事件缓存 data/espn_events_cache.json） | `scripts/fetch_espn_games.py` |
| 球员/球队赛季数据、名单、位置 | basketball-reference（league per_game/advanced/per_poss 页 + 战绩页） | `scripts/fetch_bbref_seasons.py` |
| 伤病报告 | ESPN injuries API | `scripts/fetch_injury_report.py` |

**bbref 抓取规则**：
- 必须用 **curl 子进程**（Python requests/curl_cffi 的 TLS 指纹会被 403）
- 必须挂 Clash 代理（`PROXY = http://127.0.0.1:7897`），且需保证 Clash 在运行
- 请求间隔 ≥7s；Cloudflare 质询页出现会指数退避重试，被限流时等 30 分钟再跑
- 数据页列名坑：`Tm` 列已改名 `Team`；战绩表第一列是分区名表头、数据是全名带 `*`（用 `team_id_of()` 尾词匹配）

**赔率数据现状**：
- `odds_data` 18,852 条全部来自 `scripts/import_kaggle_odds.py`（Kaggle 2025-26 赛季，最晚 2026-06-13 总决赛；8 月休赛期无新数据）
- `data_quality` 全是导入时静态盖章的 `NORMAL`——真实质量评级（赔率 vs 赛果校准对比）链路未建
- 部分场次缺胜负赔率（只有盘口）→ 前端显示 `-`、隐含概率回退 50%（无信息先验）
- 美国式赔率：负数=热门（-1100 下注 $1100 赢 $100），正数=冷门（+700 下注 $100 赢 $700）

## 预测算法

- 胜率：`1 / (1 + e^(-diff/7))`，直接从预测分差推导
- 比分：Ridge 模型优先，降级用手调系数
- 场景：只保留"常规赛"/"季后赛"，无"关键战"
- 净效率 = offensive_rating - defensive_rating（两个字段都在 DB 中）

## 数据库关键字段

| 表 | 存在的列 | 不存在的列 |
|----|---------|-----------|
| team_data | offensive_rating, defensive_rating, win_percentage, pace, points_per_game | net_rating |
| player_data | points_per_game, assists_per_game, rebounds_per_game, steals_per_game, blocks_per_game, turnovers_per_game, fg_percentage, three_percentage, ft_percentage, per, usage_rate, true_shooting_pct, effective_fg_pct | — |
| game_record | game_date, home_score, away_score, home_team_id, away_team_id, status, home_win | — |
| player_roster | player_id, team_id, season, position, jersey_number, height, weight, age, experience, games_played（UNIQUE(player_id,team_id,season)，被交易球员每队一行） | — |

注意：player_data 唯一键是 (player_id, season)——被交易球员只有一行（TOT 汇总）。per/bpm/vorp/win_shares 来自 bbref（官方 API 无此数据）。

注意：player.position **无真实数据**——fetch_nba_data.py 的 commonallplayers 接口不含位置字段；库中 477 个"有值"的是 seed_realistic_data.py `random.choice` 随机生成的假值，412 人为空。用户计划后续自行补数据，补之前位置筛选结果不可信。百分比字段存储为小数（0.471），前端 formatPct 统一 ×100 显示。
