from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class MonitorSource(db.Model):
    """监控数据源"""
    __tablename__ = 'monitor_sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    source_type = db.Column(db.String(50), default='web')  # web / rss / api
    category = db.Column(db.String(100), default='')
    crawl_method = db.Column(db.String(20), default='get')  # get / fetch / stealthy
    selectors = db.Column(db.Text, default='')  # CSS选择器JSON
    enabled = db.Column(db.Boolean, default=True)
    last_crawl_at = db.Column(db.DateTime)
    last_crawl_status = db.Column(db.String(20), default='')  # success / error

    policies = db.relationship('Article', backref='source', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'url': self.url,
            'source_type': self.source_type, 'category': self.category,
            'crawl_method': self.crawl_method, 'selectors': self.selectors,
            'enabled': self.enabled,
            'last_crawl_at': self.last_crawl_at.isoformat() if self.last_crawl_at else None,
            'last_crawl_status': self.last_crawl_status,
            'article_count': self.policies.count()
        }


class Article(db.Model):
    """采集内容条目（核心表）"""
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('monitor_sources.id'))
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(1000), default='')
    summary = db.Column(db.Text, default='')
    content = db.Column(db.Text, default='')
    pub_date = db.Column(db.Date, default=date.today)
    authority = db.Column(db.String(200), default='')  # 发布机构/来源
    category_name = db.Column(db.String(100), default='')  # 智能分类结果
    tags = db.Column(db.String(500), default='')
    content_hash = db.Column(db.String(64), unique=True, index=True)  # SHA256去重
    is_pinned = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_pub_date', 'pub_date'),
        db.Index('ix_source_id', 'source_id'),
        db.Index('ix_category', 'category_name'),
    )

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'url': self.url,
            'summary': self.summary[:200] + '...' if len(self.summary) > 200 else self.summary,
            'content': self.content,
            'pub_date': self.pub_date.isoformat() if self.pub_date else None,
            'authority': self.authority, 'category_name': self.category_name,
            'tags': self.tags, 'is_pinned': self.is_pinned,
            'is_read': self.is_read, 'view_count': self.view_count,
            'source_name': self.source.name if self.source else '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Category(db.Model):
    """知识库分类（支持二级）"""
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    sort_order = db.Column(db.Integer, default=0)
    icon = db.Column(db.String(50), default='')
    description = db.Column(db.String(500), default='')

    parent = db.relationship('Category', remote_side=[id], backref='children')
    items = db.relationship('KnowledgeItem', backref='category', lazy='dynamic')

    def to_dict(self, include_count=False):
        d = {
            'id': self.id, 'name': self.name,
            'parent_id': self.parent_id, 'sort_order': self.sort_order,
            'icon': self.icon, 'description': self.description,
            'children': [c.to_dict() for c in sorted(self.children, key=lambda x: x.sort_order)]
        }
        if include_count:
            all_ids = self._get_all_child_ids()
            d['item_count'] = KnowledgeItem.query.filter(
                KnowledgeItem.category_id.in_(all_ids)).count()
        return d

    def _get_all_child_ids(self):
        ids = [self.id]
        for child in self.children:
            ids.extend(child._get_all_child_ids())
        return ids


class KnowledgeItem(db.Model):
    """知识库条目"""
    __tablename__ = 'knowledge_items'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    title = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, default='')
    source = db.Column(db.String(500), default='')
    source_url = db.Column(db.String(1000), default='')
    tags = db.Column(db.String(500), default='')
    is_pinned = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'content': self.content,
            'source': self.source, 'source_url': self.source_url,
            'tags': self.tags, 'is_pinned': self.is_pinned,
            'view_count': self.view_count,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class User(db.Model):
    """管理员"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
