import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-trend-hub-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "instance", "aitrendhub.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CRAWL_INTERVAL_MINUTES = 120  # 每2小时抓取一次
    ITEMS_PER_PAGE = 20
    MAX_CONTENT_LENGTH = 50000  # 最大正文字数
