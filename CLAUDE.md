# NBA 预测系统 — 开发指南

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

### 前端

- `const fn = () => {...}` 定义在 `ref()` / `reactive()` 之前（避免 TDZ）
- 新页面组件放 `src/views/<name>/index.vue`
- 图标用全局注册的 Element Plus Icons 字符串名
- API 调用加 `try/catch`，catch 里至少 `console.error`

## 预测算法

- 胜率：`1 / (1 + e^(-diff/7))`，直接从预测分差推导
- 比分：Ridge 模型优先，降级用手调系数
- 场景：只保留"常规赛"/"季后赛"，无"关键战"
- 净效率 = offensive_rating - defensive_rating（两个字段都在 DB 中）

## 数据库关键字段

| 表 | 存在的列 | 不存在的列 |
|----|---------|-----------|
| team_data | offensive_rating, defensive_rating, win_percentage, pace, points_per_game | net_rating |
| player_data | points_per_game, assists_per_game, rebounds_per_game, per, usage_rate | — |
| game_record | game_date, home_score, away_score, home_team_id, away_team_id, status, home_win | — |
