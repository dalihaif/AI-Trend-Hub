"""AI趋势雷达 - 定时调度"""
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(daemon=True)


def start_scheduler(app, interval_minutes=120):
    """启动定时抓取任务"""
    def crawl_job():
        with app.app_context():
            from crawler import crawl_all
            logger.info("定时抓取任务开始...")
            total = crawl_all(app)
            logger.info(f"定时抓取完成，新增 {total} 条")

    scheduler.add_job(
        crawl_job,
        'interval',
        minutes=interval_minutes,
        id='ai_crawl',
        name='AI趋势定时抓取',
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"定时调度器已启动，间隔 {interval_minutes} 分钟")
