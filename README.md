# NBA球员与球队表现预测系统

## 项目概述

基于数据驱动的NBA球员与球队表现预测系统，采用纯统计学方法（非AI），支持双版本预测（纯系统 vs 系统+赔率融合）。

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端表现层                            │
│              Vue3 + Element Plus + ECharts               │
└─────────────────────────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────────────────────────────────────┐
│                    后端服务层                            │
│                SpringBoot 3.2 + MyBatis-Plus            │
└─────────────────────────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────────────────────────────────────┐
│                    算法计算层                            │
│               Python + FastAPI + Pandas + Sklearn        │
└─────────────────────────────────────────────────────────┘
                          │ JDBC
┌─────────────────────────────────────────────────────────┐
│                    数据持久层                            │
│                        MySQL 8.0                         │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
nba-predict/
├── nba-predict-sql/          # 数据库脚本
│   └── init.sql              # 建表和初始化数据
├── nba-predict-backend/      # SpringBoot后端
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/nba/predict/
│   │   │   │   ├── config/       # 配置类
│   │   │   │   ├── controller/   # 控制器
│   │   │   │   ├── service/      # 服务层
│   │   │   │   ├── mapper/       # MyBatis映射
│   │   │   │   ├── entity/       # 实体类
│   │   │   │   ├── common/       # 公共类
│   │   │   │   ├── exception/    # 异常处理
│   │   │   │   └── util/         # 工具类
│   │   │   └── resources/
│   │   │       └── application.yml
│   │   └── test/
│   └── pom.xml
├── nba-predict-algorithm/    # Python算法层
│   ├── app/
│   │   ├── api/              # API路由
│   │   ├── core/             # 核心配置
│   │   ├── models/           # 数据模型
│   │   ├── services/         # 业务服务
│   │   └── utils/            # 工具函数
│   ├── config/               # 配置文件
│   ├── data/                 # 数据目录
│   ├── logs/                 # 日志目录
│   ├── tests/                # 测试文件
│   ├── main.py               # 入口文件
│   └── requirements.txt
├── nba-predict-frontend/     # Vue3前端
│   ├── src/
│   │   ├── api/              # API调用
│   │   ├── assets/           # 静态资源
│   │   ├── components/       # 公共组件
│   │   ├── layouts/          # 布局组件
│   │   ├── router/           # 路由配置
│   │   ├── stores/           # 状态管理
│   │   ├── styles/           # 样式文件
│   │   ├── utils/            # 工具函数
│   │   └── views/            # 页面组件
│   ├── public/
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 环境要求

| 组件 | 版本 |
|------|------|
| JDK | 17+ |
| Maven | 3.8+ |
| Python | 3.10+ |
| Node.js | 18+ |
| MySQL | 8.0+ |

## 快速开始

### 1. 数据库初始化

```bash
# 登录MySQL
mysql -u root -p

# 执行初始化脚本
source nba-predict-sql/init.sql
```

### 2. 启动后端

```bash
cd nba-predict-backend

# 修改数据库配置
# vim src/main/resources/application.yml

# 编译运行
mvn clean package
java -jar target/nba-predict-backend-1.0.0.jar
```

### 3. 启动算法层

```bash
cd nba-predict-algorithm

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

### 4. 启动前端

```bash
cd nba-predict-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 5. 访问系统

- 前端: http://localhost:3000
- 后端API: http://localhost:8080/api
- 算法层API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 核心功能

### 球员预测
- KMeans聚类分类（7大类）
- 多维度系数计算（全明星、老将、伤病等）
- 预测区间输出（拉胯/常规/爆发）

### 球队预测
- 球队风格分类（3防4攻）
- 克制关系分析
- 双版本预测（纯系统 vs 融合）

### 赔率管理
- 多数据源采集（球探网、Covers等）
- 数据源评估（MAE、校准度等5维度）
- 自动切换机制

### 数据看板
- 预测误差统计
- 数据源评分对比
- 球员稳定性趋势

## 系数初始值

| 系数 | 范围 | 初始值 |
|------|------|--------|
| 全明星系数 | 1.00~1.40 | 1.20 |
| 老将系数 | 0.80~0.95 | 0.875 |
| 伤病系数 | 0.70~1.00 | 0.85 |
| 关键球系数 | 0.70~1.30 | 1.00 |
| 主场系数 | 1.03~1.08 | 1.055 |
| 疲劳系数 | 0.92~1.00 | 0.96 |
| 赔率权重 | 0~30% | 20% |

## 开发说明

- 前端: Vue3 + Element Plus + ECharts
- 后端: SpringBoot 3.2 + MyBatis-Plus
- 算法: Python + FastAPI + Pandas + Scikit-learn
- 数据库: MySQL 8.0

## 注意事项

1. 首次运行需先初始化数据库
2. 算法层需要单独启动
3. 赔率采集需要配置数据源
4. 预测精度依赖历史数据量

## License

MIT
