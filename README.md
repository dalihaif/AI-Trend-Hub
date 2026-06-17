# AI-Trend-Hub (AI趋势雷达)

AI 资讯聚合与知识库管理平台 — 自动抓取 14 个 AI 数据源，智能分类，正文提取，定时更新。

## 功能特性

- **14 个 AI 数据源**：机器之心、量子位、36氪、GitHub Trending、Hacker News API、TechCrunch、IT之家、CSDN-AI、InfoQ-AI、51CTO-AI、品玩、AI工具集、OpenAI Blog、Microsoft-AI
- **正文提取**：基于 readability-lxml (Mozilla Readability) 自动提取文章正文，提取失败时引导查看原文
- **智能分类**：60+ AI 关键词权重匹配，自动归入 9 大分类
- **SHA256 去重**：内容哈希去重，避免重复入库
- **管理后台**：数据源/文章/分类/知识库 CRUD，批量操作，一键全量抓取
- **定时抓取**：APScheduler 每 2 小时自动更新
- **一键启动**：`start.bat` 自动检测/安装 Python 环境并启动服务

## 快速开始

### 方式一：一键启动（推荐）

直接双击 `start.bat`，脚本会自动：
1. 检测系统 Python（需 >= 3.10）
2. 未检测到则自动下载便携版 Python 3.12
3. 安装所有依赖
4. 启动服务并打开浏览器

### 方式二：手动启动

```bash
pip install -r requirements.txt
python app.py
```

服务启动后访问：
- 前台首页：http://127.0.0.1:5000
- 管理后台：http://127.0.0.1:5000/admin
- 默认账号：`admin` / `admin123`

## 技术栈

- **后端**：Flask + SQLAlchemy + APScheduler
- **前端**：Bootstrap 5.3 + Bootstrap Icons
- **爬虫**：Scrapling (可选) → requests 降级 → readability-lxml 正文提取
- **数据库**：SQLite（零配置）

## 项目结构

```
├── app.py              # 应用入口
├── config.py           # 配置
├── models.py           # 数据模型 (5张表)
├── crawler.py          # 爬虫引擎 (14个数据源 + 正文提取)
├── scheduler.py        # 定时任务
├── requirements.txt    # Python 依赖
├── start.bat           # 一键启动脚本
├── routes/
│   ├── main.py         # 前台路由
│   └── admin.py        # 管理后台路由
└── templates/          # Jinja2 模板 (13个)
```

## License

MIT
