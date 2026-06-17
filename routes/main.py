"""前台路由"""
from flask import Blueprint, render_template, request
from models import db, Article, Category, KnowledgeItem, MonitorSource
from sqlalchemy import func

bp = Blueprint('main', __name__)

CATEGORIES = ['AI热点新闻', 'Agent工具', 'AI Skills', 'AI工具推荐', '开源项目', '大模型动态', 'AI创作', '技术教程', '技术社区']


@bp.route('/')
def index():
    """仪表盘首页"""
    stats = {
        'total_articles': Article.query.count(),
        'total_sources': MonitorSource.query.filter_by(enabled=True).count(),
        'today_articles': Article.query.filter(
            Article.pub_date == func.current_date()).count(),
        'total_knowledge': KnowledgeItem.query.count(),
    }
    # 各分类文章数
    cat_counts = {}
    for cat in CATEGORIES:
        cat_counts[cat] = Article.query.filter_by(category_name=cat).count()

    # 最新10条
    recent = Article.query.order_by(
        Article.is_pinned.desc(), Article.pub_date.desc(), Article.id.desc()
    ).limit(10).all()

    return render_template('main/index.html', stats=stats, cat_counts=cat_counts,
                           recent=recent, categories=CATEGORIES)


@bp.route('/articles')
def articles():
    """文章列表"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search = request.args.get('q', '')
    source_id = request.args.get('source', 0, type=int)

    query = Article.query
    if category:
        query = query.filter_by(category_name=category)
    if source_id:
        query = query.filter_by(source_id=source_id)
    if search:
        query = query.filter(Article.title.ilike(f'%{search}%'))

    pagination = query.order_by(
        Article.is_pinned.desc(), Article.pub_date.desc(), Article.id.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    sources = MonitorSource.query.filter_by(enabled=True).all()
    return render_template('main/articles.html', pagination=pagination,
                           category=category, search=search, source_id=source_id,
                           sources=sources, categories=CATEGORIES)


@bp.route('/articles/<int:article_id>')
def article_detail(article_id):
    """文章详情"""
    article = Article.query.get_or_404(article_id)
    if not article.is_read:
        article.is_read = True
        article.view_count += 1
        db.session.commit()
    return render_template('main/article_detail.html', article=article)


@bp.route('/knowledge')
def knowledge():
    """知识库"""
    cats = Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()
    cat_data = []
    for cat in cats:
        all_ids = cat._get_all_child_ids()
        count = KnowledgeItem.query.filter(KnowledgeItem.category_id.in_(all_ids)).count()
        cat_data.append({'cat': cat, 'count': count})
    return render_template('main/knowledge.html', cat_data=cat_data)


@bp.route('/knowledge/<int:item_id>')
def knowledge_detail(item_id):
    """知识条目详情"""
    item = KnowledgeItem.query.get_or_404(item_id)
    item.view_count += 1
    db.session.commit()
    return render_template('main/knowledge_detail.html', item=item)
