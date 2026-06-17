"""后台管理路由"""
import hashlib
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, Article, Category, KnowledgeItem, MonitorSource, User
from crawler import crawl_source, crawl_all, suggest_category

bp = Blueprint('admin', __name__, url_prefix='/admin')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


# ========== 认证 ==========
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        user = User.query.filter_by(username=u).first()
        if user and user.password_hash == hashlib.sha256(p.encode()).hexdigest():
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html', error='用户名或密码错误')
    return render_template('admin/login.html', error='')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


# ========== 仪表盘 ==========
@bp.route('/')
@login_required
def dashboard():
    stats = {
        'articles': Article.query.count(),
        'sources': MonitorSource.query.count(),
        'sources_active': MonitorSource.query.filter_by(enabled=True).count(),
        'knowledge': KnowledgeItem.query.count(),
        'today_articles': Article.query.filter(
            Article.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


# ========== 数据源 CRUD ==========
@bp.route('/sources')
@login_required
def sources_page():
    sources = MonitorSource.query.order_by(MonitorSource.id.desc()).all()
    return render_template('admin/sources.html', sources=sources)


@bp.route('/api/sources', methods=['POST'])
@login_required
def create_source():
    data = request.get_json()
    src = MonitorSource(
        name=data.get('name', ''), url=data.get('url', ''),
        source_type=data.get('source_type', 'web'),
        category=data.get('category', ''),
        crawl_method=data.get('crawl_method', 'get'),
        selectors=data.get('selectors', ''),
    )
    db.session.add(src)
    db.session.commit()
    return jsonify({'success': True, 'id': src.id})


@bp.route('/api/sources/<int:sid>', methods=['PUT'])
@login_required
def update_source(sid):
    src = MonitorSource.query.get_or_404(sid)
    data = request.get_json()
    for k in ['name', 'url', 'source_type', 'category', 'crawl_method', 'selectors', 'enabled']:
        if k in data:
            setattr(src, k, data[k])
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/sources/<int:sid>', methods=['DELETE'])
@login_required
def delete_source(sid):
    src = MonitorSource.query.get_or_404(sid)
    db.session.delete(src)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/sources/<int:sid>/crawl', methods=['POST'])
@login_required
def crawl_one(sid):
    src = MonitorSource.query.get_or_404(sid)
    count = crawl_source(src)
    return jsonify({'success': True, 'new_count': count})


# ========== 文章管理 ==========
@bp.route('/articles')
@login_required
def articles_page():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search = request.args.get('q', '')
    query = Article.query
    if category:
        query = query.filter_by(category_name=category)
    if search:
        query = query.filter(Article.title.ilike(f'%{search}%'))
    pagination = query.order_by(Article.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/articles.html', pagination=pagination, category=category, search=search)


@bp.route('/api/articles/<int:aid>', methods=['GET'])
@login_required
def get_article(aid):
    a = Article.query.get_or_404(aid)
    return jsonify({'success': True, 'item': a.to_dict()})


@bp.route('/api/articles/<int:aid>', methods=['PUT'])
@login_required
def update_article(aid):
    a = Article.query.get_or_404(aid)
    data = request.get_json()
    for k in ['title', 'summary', 'category_name', 'tags', 'is_pinned']:
        if k in data:
            setattr(a, k, data[k])
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/articles/<int:aid>', methods=['DELETE'])
@login_required
def delete_article(aid):
    a = Article.query.get_or_404(aid)
    db.session.delete(a)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/articles/batch', methods=['PUT'])
@login_required
def batch_update_articles():
    data = request.get_json()
    ids = data.get('ids', [])
    updates = data.get('updates', {})
    for aid in ids:
        a = Article.query.get(aid)
        if a:
            for k, v in updates.items():
                if k in ['category_name', 'tags', 'is_pinned']:
                    setattr(a, k, v)
    db.session.commit()
    return jsonify({'success': True, 'updated': len(ids)})


@bp.route('/api/articles/batch-delete', methods=['POST'])
@login_required
def batch_delete_articles():
    data = request.get_json()
    ids = data.get('ids', [])
    Article.query.filter(Article.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True, 'deleted': len(ids)})


@bp.route('/api/articles/batch-to-knowledge', methods=['POST'])
@login_required
def batch_to_knowledge():
    data = request.get_json()
    ids = data.get('ids', [])
    cat_id = data.get('category_id')
    count = 0
    for aid in ids:
        a = Article.query.get(aid)
        if a:
            ki = KnowledgeItem(
                category_id=cat_id, title=a.title,
                content=a.content or a.summary, source=a.authority,
                source_url=a.url, tags=a.tags,
            )
            db.session.add(ki)
            count += 1
    db.session.commit()
    return jsonify({'success': True, 'transferred': count})


@bp.route('/api/articles/batch-suggest', methods=['POST'])
@login_required
def batch_suggest():
    data = request.get_json()
    ids = data.get('ids', [])
    suggestions = []
    for aid in ids:
        a = Article.query.get(aid)
        if a:
            cat = suggest_category(a.title, a.authority)
            suggestions.append({'id': a.id, 'title': a.title, 'suggested': cat})
    return jsonify({'success': True, 'suggestions': suggestions})


# ========== 分类管理 ==========
@bp.route('/categories')
@login_required
def categories_page():
    cats = Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()
    return render_template('admin/categories.html', categories=cats)


@bp.route('/api/categories', methods=['POST'])
@login_required
def create_category():
    data = request.get_json()
    cat = Category(
        name=data.get('name', ''), parent_id=data.get('parent_id'),
        sort_order=data.get('sort_order', 0), icon=data.get('icon', ''),
        description=data.get('description', ''),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify({'success': True, 'id': cat.id})


@bp.route('/api/categories/<int:cid>', methods=['PUT'])
@login_required
def update_category(cid):
    cat = Category.query.get_or_404(cid)
    data = request.get_json()
    for k in ['name', 'parent_id', 'sort_order', 'icon', 'description']:
        if k in data:
            setattr(cat, k, data[k])
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/categories/<int:cid>', methods=['DELETE'])
@login_required
def delete_category(cid):
    cat = Category.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'success': True})


# ========== 知识库管理 ==========
@bp.route('/knowledge')
@login_required
def knowledge_page():
    cats = Category.query.order_by(Category.sort_order).all()
    items = KnowledgeItem.query.order_by(KnowledgeItem.id.desc()).limit(100).all()
    return render_template('admin/knowledge.html', items=items, categories=cats)


@bp.route('/api/knowledge', methods=['POST'])
@login_required
def create_knowledge():
    data = request.get_json()
    ki = KnowledgeItem(
        category_id=data.get('category_id'),
        title=data.get('title', ''), content=data.get('content', ''),
        source=data.get('source', ''), source_url=data.get('source_url', ''),
        tags=data.get('tags', ''),
    )
    db.session.add(ki)
    db.session.commit()
    return jsonify({'success': True, 'id': ki.id})


@bp.route('/api/knowledge/<int:kid>', methods=['GET'])
@login_required
def get_knowledge(kid):
    ki = KnowledgeItem.query.get_or_404(kid)
    return jsonify({'success': True, 'item': ki.to_dict()})


@bp.route('/api/knowledge/<int:kid>', methods=['PUT'])
@login_required
def update_knowledge(kid):
    ki = KnowledgeItem.query.get_or_404(kid)
    data = request.get_json()
    for k in ['category_id', 'title', 'content', 'source', 'source_url', 'tags', 'is_pinned']:
        if k in data:
            setattr(ki, k, data[k])
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/knowledge/<int:kid>', methods=['DELETE'])
@login_required
def delete_knowledge(kid):
    ki = KnowledgeItem.query.get_or_404(kid)
    db.session.delete(ki)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/knowledge/batch', methods=['PUT'])
@login_required
def batch_update_knowledge():
    data = request.get_json()
    ids = data.get('ids', [])
    updates = data.get('updates', {})
    for kid in ids:
        ki = KnowledgeItem.query.get(kid)
        if ki:
            for k, v in updates.items():
                if k in ['category_id', 'tags', 'is_pinned']:
                    setattr(ki, k, v)
    db.session.commit()
    return jsonify({'success': True, 'updated': len(ids)})


@bp.route('/api/knowledge/batch-suggest', methods=['POST'])
@login_required
def batch_suggest_knowledge():
    data = request.get_json()
    ids = data.get('ids', [])
    suggestions = []
    for kid in ids:
        ki = KnowledgeItem.query.get(kid)
        if ki:
            cat = suggest_category(ki.title, '')
            suggestions.append({'id': ki.id, 'title': ki.title, 'suggested': cat})
    return jsonify({'success': True, 'suggestions': suggestions})


# ========== 全量抓取 & 统计 ==========
@bp.route('/api/crawl-all', methods=['POST'])
@login_required
def crawl_all_api():
    from flask import current_app
    count = crawl_all(current_app)
    return jsonify({'success': True, 'new_count': count})


@bp.route('/api/stats')
@login_required
def stats():
    return jsonify({
        'articles': Article.query.count(),
        'sources': MonitorSource.query.count(),
        'sources_active': MonitorSource.query.filter_by(enabled=True).count(),
        'knowledge': KnowledgeItem.query.count(),
    })
