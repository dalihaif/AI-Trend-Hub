"""AI趋势雷达 - 应用入口"""
import os
import sys
import hashlib
import logging

from flask import Flask
from config import Config
from models import db, User, Category

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保 instance 目录存在 (SQLite 需要)
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_dir, exist_ok=True)

    db.init_app(app)

    # 注册蓝图
    from routes.main import bp as main_bp
    from routes.admin import bp as admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        _ensure_admin_user()
        _seed_categories()
        _seed_default_sources()

    # 启动定时调度
    from scheduler import start_scheduler
    start_scheduler(app, app.config.get('CRAWL_INTERVAL_MINUTES', 120))

    return app


def _ensure_admin_user():
    """确保存在管理员账户"""
    if not User.query.filter_by(username='admin').first():
        user = User(
            username='admin',
            password_hash=hashlib.sha256('admin123'.encode()).hexdigest(),
        )
        db.session.add(user)
        db.session.commit()
        logger.info("已创建默认管理员账户: admin / admin123")


def _seed_categories():
    """预置AI领域分类"""
    if Category.query.count() > 0:
        return
    cats = [
        Category(name='AI热点新闻', sort_order=1, icon='bi-lightning-charge', description='AI行业重大新闻、融资、政策'),
        Category(name='大模型动态', sort_order=2, icon='bi-cpu', description='GPT、Claude、Gemini等大模型发布与更新'),
        Category(name='Agent工具', sort_order=3, icon='bi-robot', description='AI Agent、智能体、自动化工作流'),
        Category(name='AI Skills', sort_order=4, icon='bi-puzzle', description='插件、Skills、Prompt、扩展能力'),
        Category(name='AI工具推荐', sort_order=5, icon='bi-star', description='好用的AI工具和效率神器'),
        Category(name='AI创作', sort_order=6, icon='bi-palette', description='AI绘画、视频生成、AIGC'),
        Category(name='开源项目', sort_order=7, icon='bi-github', description='GitHub热门AI开源项目'),
        Category(name='技术教程', sort_order=8, icon='bi-book', description='AI技术教程、实战指南'),
        Category(name='技术社区', sort_order=9, icon='bi-people', description='HackerNews、Reddit等技术社区热帖'),
    ]
    db.session.add_all(cats)
    db.session.commit()
    logger.info("已预置9个AI领域分类")


def _seed_default_sources():
    """预置数据源"""
    from crawler import seed_default_sources
    from models import MonitorSource
    if MonitorSource.query.count() == 0:
        seed_default_sources()
        logger.info("已预置AI领域数据源")


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"AI趋势雷达启动中 → http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
