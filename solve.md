# NBA 预测系统 v2 — 问题与修复记录

> 记录 v2 重构（2026年8月10日）中遇到的所有运行时问题及解决方案。

---

## 一、运行时崩溃

### 1.1 预测按钮 → "服务器异常"

**现象**：点击"开始预测"，弹窗"预测失败"，后端日志 `MissingServletRequestParameterException`

**根因**：前端 `axios.post(url, { playerId: 1 })` 发 JSON body，但 Controller 用 `@RequestParam` 从 query string 读参数，Spring 找不到 → 400 → 全局异常处理返回 500

**修复**：
```java
// 之前
@PostMapping("/predict")
public Result<Object> predict(@RequestParam Long playerId, ...)

// 之后
@PostMapping("/predict")
public Result<Object> predict(@RequestBody PlayerPredictRequest request)
```
新增 `PlayerPredictRequest` 和 `TeamPredictRequest` 两个 DTO record。

---

### 1.2 编译错误 `STAR_NOT_FOUND`

**现象**：`java: 找不到符号 变量 STAR_NOT_FOUND`

**根因**：重构 `SeriesStarServiceImpl.getStarDetail()` 时引用 `ResultCode.STAR_NOT_FOUND`，但忘了在枚举里加这个值

**修复**：`ResultCode` 补上 `STAR_NOT_FOUND(1007, "系列赛之星不存在")`

---

### 1.3 `/player/list` NPE → 所有列表页崩溃

**现象**：`系统异常: /api/player/list - null`，球队名称数据显示为空

**根因**：代码审查时在所有 Controller 类上加 `@Validated` 以激活 `@Min`/`@Max` 校验，但 `@Validated` + `@RestController` 触发 Spring AOP 代理冲突，方法参数解析时抛出 NPE

**修复**：从 8 个 Controller 全部移除 `@Validated`，`@Min`/`@Max` 注解保留作为文档

---

### 1.4 前端白屏 "什么都没有"

**现象**：打开 `localhost:3000` 白屏，Console 报 `ReferenceError: Cannot access 'formatDateStr' before initialization`

**根因**：`home/index.vue` 中 `const selectedDate = ref(formatDateStr(new Date()))` 在初始化时调用了 `formatDateStr`，但该函数作为 `const` 在后面才定义（TDZ 暂时性死区）

**修复**：将 `formatDateStr` 函数定义移到 `selectedDate` 等 `ref()` 初始化之前

---

## 二、API 路由/代理错误

### 2.1 `/data/players` 500

**现象**：`GET http://localhost:3000/api/data/players?...` → 500

**根因**：`request.js` 的 `baseURL: '/api'` 给所有请求加前缀。`dataApi` 调用 `/data/players` 实际发出 `/api/data/players`，被 Vite 代理到 Java 后端（8080），Java 没有 `/data` 端点

**修复**：
1. `request.js` 新建 `pythonRequest` 实例（baseURL 为空，无 `/api` 前缀）
2. `api/index.js` 中 `dataApi` 全部改用 `pythonRequest`
3. `vite.config.js` 代理新增 `/data` 和 `/algorithm` → `localhost:8000`

---

### 2.2 交手记录 500

**现象**：`GET /api/team/battle/record?teamId1=2&teamId2=3` → 500

**根因**：
- 路径不存在：后端是 `GameRecordController` 的 `/game/battle`
- 参数名不对：前端 `teamId1/teamId2`，后端期望 `team1Id/team2Id`

**修复**：
- `api/index.js`：`teamApi.getBattleRecord` 路径改为 `/game/battle`
- `predict/index.vue`：参数名 `teamId1` → `team1Id`

---

### 2.3 后台更新失败

**现象**：`后台更新失败: run() got an unexpected keyword argument 'skip_retrain'`

**根因**：`main.py` 中 `_bg_update` 调用 `run(skip_retrain=True)`，但 `scripts/daily_update.py` 的 `run()` 没有任何参数

**修复**：移除 `skip_retrain=True`

---

## 三、前端数据映射

### 3.1 球员搜索下拉框为空

**现象**：输入球员名搜索，下拉框无结果显示

**根因**：`el-option` 绑定 `item.id` / `item.name`，但后端返回 `playerId` / `playerName`

**修复**：`player/predict.vue` 的 option 改为 `:key="item.playerId" :label="item.playerName" :value="item.playerId"`

---

### 3.2 球员数据表格无数据

**现象**：球员列表表格空白

**根因**：Python 返回 `points_per_game`（snake_case），Vue 表格列 `prop="pointsPerGame"`（驼峰）不匹配

**修复**：`players/index.vue` 新增 `toCamel()` 映射函数，在 `loadPlayers()` 中将 API 响应的蛇形键转为驼峰键

---

### 3.3 预测结果界面永远 "客队占优"

**现象**：后端日志显示预测正确（如雷霆 130-105 奇才），前端界面却显示客胜、比分全为 0

**根因**：Python 返回 `predict_home_score`（蛇形），前端模板读 `result.predictHomeScore`（驼峰）→ `undefined` → 全为 0 → `predictScoreDiff = 0` → 永远客胜

**修复**：所有字段引用加 `??` 降级：`(result.predictHomeScore ?? result.predict_home_score ?? 0)`

---

## 四、预测算法

### 4.1 所有比赛胜率 ~50%

**现象**：强队 vs 弱队胜率差异极小，"没拉开差距"

**根因**：
1. `_calc_win_probability` 使用 `net_rating` 字段，该字段不在数据库中（是 Python 运行时计算字段，通常为 null）
2. log5 除数 400 对 NBA 净效率值（±15）来说太大，净效率差 10 分只影响 ~1%

**修复**：
1. 改用真实 DB 字段 `offensive_rating - defensive_rating` 计算净效率
2. 加入 `win_percentage` 差加权
3. sigmoid 除数从 400 降到 12

---

### 4.2 胜率与预测比分矛盾

**现象**：胜率条显示"主队 55%"，但预测比分客队更高

**根因**：胜率公式和 Ridge 模型独立计算，互不知情，可能得出相反结论

**修复**：胜率直接从预测分差推导 — `win_prob = 1 / (1 + e^(-diff/7))`

| 分差 | 主队胜率 |
|------|----------|
| 0 | 50% |
| ±1 | 54% / 46% |
| ±5 | 67% / 33% |
| ±10 | 81% / 19% |
| ±15 | 90% / 10% |

---

## 五、环境配置

### 5.1 本地启动失败（数据库连接）

**现象**：Java 后端启动报数据库连接失败

**根因**：安全性修复移除 `DB_PASSWORD` 默认值 → `${DB_PASSWORD}` 无环境变量时为空

**修复**：恢复 `${DB_PASSWORD:223688}` 本地开发默认值，生产通过环境变量覆盖

---

### 5.2 Sass 弃用警告

**现象**：`Deprecation Warning: The legacy JS API is deprecated`

**修复**：`vite.config.js` scss 配置加 `api: 'modern'`

---

## 核心教训

1. **字段名不一致是最大坑**：Python（snake_case）→ Java（Map 原样传递）→ 前端（camelCase）三层传递，每层都可能打破命名约定
2. **不要用 `@Validated` 在 Controller 类上**：Spring AOP 代理与 MVC 请求映射冲突，间歇性 NPE 难以排查
3. **`baseURL: '/api'` 的 axios 实例不要用于调用其他服务**：创建独立的请求实例各走各的代理
4. **新页面先看 Console**：TDZ 错误是白屏的 90% 原因，函数定义放 `ref()` 前面就行
