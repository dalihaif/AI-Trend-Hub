"""
AI趋势雷达 - 爬虫引擎
四级抓取策略 + 正文提取 + 智能分类 + SHA256去重
"""
import hashlib
import json
import re
import time
import logging
from datetime import datetime, date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# ========== AI领域数据源预置 ==========
DEFAULT_AI_SOURCES = [
    {
        'name': '机器之心',
        'url': 'https://www.jiqizhixin.com/',
        'source_type': 'web',
        'category': 'AI综合资讯',
        'crawl_method': 'get',
        'selectors': json.dumps({
            'list': '.article-item',
            'title': 'a',
            'link': 'a',
            'summary': '.article-item__summary',
        })
    },
    {
        'name': '量子位',
        'url': 'https://www.qbitai.com/',
        'source_type': 'web',
        'category': 'AI综合资讯',
        'crawl_method': 'get',
        'selectors': json.dumps({
            'list': '.post-list-item',
            'title': '.post-title a',
            'link': '.post-title a',
        })
    },
    {
        'name': '36氪AI频道',
        'url': 'https://36kr.com/information/AI/',
        'source_type': 'web',
        'category': 'AI综合资讯',
        'crawl_method': 'get',
        'selectors': json.dumps({
            'list': '.article-item-title',
            'title': 'a',
            'link': 'a',
        })
    },
    {
        'name': 'GitHub Trending',
        'url': 'https://github.com/trending?since=daily',
        'source_type': 'web',
        'category': '开源项目',
        'crawl_method': 'get',
        'selectors': json.dumps({
            'list': 'article.Box-row',
            'title': 'h2 a',
            'link': 'h2 a',
            'summary': 'p',
        })
    },
    {
        'name': 'Hacker News - AI',
        'url': 'https://hacker-news.firebaseio.com/v0/topstories.json',
        'source_type': 'api',
        'category': '技术社区',
        'crawl_method': 'hn_api',
        'selectors': ''
    },
    {
        'name': 'AI工具集',
        'url': 'https://ai-bot.cn/',
        'source_type': 'web',
        'category': 'AI工具',
        'crawl_method': 'get',
        'selectors': ''
    },
    {
        'name': 'OpenAI Blog',
        'url': 'https://openai.com/blog',
        'source_type': 'web',
        'category': '大模型动态',
        'crawl_method': 'get',
        'selectors': ''
    },
    {
        'name': '51CTO-AI',
        'url': 'https://www.51cto.com/ai',
        'source_type': 'web',
        'category': 'AI综合资讯',
        'crawl_method': 'get',
        'selectors': ''
    },
    {
        'name': 'InfoQ-AI',
        'url': 'https://www.infoq.cn/topic/AI',
        'source_type': 'web',
        'category': '技术教程',
        'crawl_method': 'get',
        'selectors': ''
    },
    {
        'name': 'CSDN-AI',
        'url': 'https://blog.csdn.net/nav/ai',
        'source_type': 'web',
        'category': '技术教程',
        'crawl_method': 'get',
        'selectors': ''
    },
    {
        'name': 'IT之家-AI',
        'url': 'https://www.ithome.com/tags/AI/',
        'source_type': 'web',
        'category': 'AI热点新闻',
        'crawl_method': 'get',
        'selectors': json.dumps({
            'list': '.ul-list li',
            'title': 'a',
            'link': 'a',
        })
    },
    {
        'name': 'TechCrunch-AI',
        'url': 'https://techcrunch.com/category/artificial-intelligence/',
        'source_type': 'web',
        'category': 'AI热点新闻',
        'crawl_method': 'get',
        'selectors': json.dumps({
            'list': '.post-block',
            'title': '.post-block__title a',
            'link': '.post-block__title a',
            'summary': '.post-block__content p',
        })
    },
    {
        'name': '品玩',
        'url': 'https://www.pingwest.com/',
        'source_type': 'web',
        'category': 'AI综合资讯',
        'crawl_method': 'get',
        'selectors': ''
    },
    {
        'name': 'Microsoft-AI',
        'url': 'https://news.microsoft.com/source/topics/ai/',
        'source_type': 'web',
        'category': '大模型动态',
        'crawl_method': 'get',
        'selectors': ''
    },
]

# ========== 智能分类关键词 (AI领域) ==========
CATEGORY_KEYWORDS = {
    # 大模型动态
    'GPT': ('大模型动态', 20), 'Claude': ('大模型动态', 20), 'Gemini': ('大模型动态', 20),
    'Llama': ('大模型动态', 18), '大模型': ('大模型动态', 18), 'LLM': ('大模型动态', 18),
    '语言模型': ('大模型动态', 15), 'Transformer': ('大模型动态', 15),
    '参数': ('大模型动态', 8), '微调': ('大模型动态', 12), '训练': ('大模型动态', 10),
    'DeepSeek': ('大模型动态', 20), '通义': ('大模型动态', 18), '文心': ('大模型动态', 18),
    'Kimi': ('大模型动态', 18), 'Qwen': ('大模型动态', 18),
    # Agent工具
    'Agent': ('Agent工具', 20), '智能体': ('Agent工具', 20), 'AutoGPT': ('Agent工具', 20),
    'Coze': ('Agent工具', 18), 'Dify': ('Agent工具', 18), 'workflow': ('Agent工具', 15),
    '工作流': ('Agent工具', 15), '自主': ('Agent工具', 10), 'multi-agent': ('Agent工具', 18),
    'MCP': ('Agent工具', 18),
    # AI Skills/插件
    'Skill': ('AI Skills', 18), '插件': ('AI Skills', 18), 'Plugin': ('AI Skills', 18),
    '扩展': ('AI Skills', 12), 'API': ('AI Skills', 10), 'SDK': ('AI Skills', 12),
    'Prompt': ('AI Skills', 15), '提示词': ('AI Skills', 15),
    # 开源项目
    'GitHub': ('开源项目', 18), '开源': ('开源项目', 20), 'stars': ('开源项目', 15),
    '仓库': ('开源项目', 12), 'repo': ('开源项目', 15), '框架': ('开源项目', 10),
    # AI工具推荐
    '工具': ('AI工具推荐', 15), '推荐': ('AI工具推荐', 12), '好用': ('AI工具推荐', 12),
    '效率': ('AI工具推荐', 10), '神器': ('AI工具推荐', 15), '必备': ('AI工具推荐', 12),
    '免费': ('AI工具推荐', 8),
    # 技术教程
    '教程': ('技术教程', 18), '指南': ('技术教程', 15), 'tutorial': ('技术教程', 18),
    '入门': ('技术教程', 12), '实战': ('技术教程', 12), '手把手': ('技术教程', 15),
    '部署': ('技术教程', 10), '搭建': ('技术教程', 10),
    # AI热点新闻
    '发布': ('AI热点新闻', 10), '融资': ('AI热点新闻', 15), '估值': ('AI热点新闻', 15),
    '收购': ('AI热点新闻', 15), '监管': ('AI热点新闻', 12), '政策': ('AI热点新闻', 12),
    '突破': ('AI热点新闻', 10), '重磅': ('AI热点新闻', 12),
    # AI绘画/视频
    '绘画': ('AI创作', 15), '生成图': ('AI创作', 15), 'Midjourney': ('AI创作', 20),
    'Stable Diffusion': ('AI创作', 20), 'Sora': ('AI创作', 20), '视频生成': ('AI创作', 18),
    '图像生成': ('AI创作', 15), 'AIGC': ('AI创作', 12),
}


def suggest_category(title, source_category=''):
    """智能分类建议"""
    scores = {}
    title_lower = title.lower() if title else ''
    for keyword, (cat_name, weight) in CATEGORY_KEYWORDS.items():
        if keyword.lower() in title_lower:
            scores[cat_name] = scores.get(cat_name, 0) + weight
    # 如果无匹配，用数据源自身的分类
    if not scores and source_category:
        return source_category
    if not scores:
        return 'AI热点新闻'
    return max(scores, key=scores.get)


# ========== 文章正文提取 ==========

def fetch_article_content(url, max_retries=1):
    """
    访问文章URL，提取正文HTML内容。
    优先使用 readability 算法，降级到 BeautifulSoup 启发式提取。
    返回 (html_content, success) 元组。
    """
    if not url or not url.startswith('http'):
        return '', False

    html = fetch_html(url)
    if not html:
        return '', False

    # 策略1: readability-lxml（Mozilla Readability 算法）
    try:
        from readability import Document
        doc = Document(html)
        content_html = doc.summary()
        if content_html and len(content_html) > 200:
            # 清洗：移除多余标签，保留核心内容
            soup = BeautifulSoup(content_html, 'lxml')
            _clean_soup(soup)
            result = str(soup)
            if len(result) > 150:
                return result, True
    except Exception as e:
        logger.debug(f"readability failed for {url}: {e}")

    # 策略2: BeautifulSoup 启发式提取
    try:
        soup = BeautifulSoup(html, 'lxml')
        _clean_soup(soup)

        # 尝试常见正文容器
        for selector in ['article', '.article-content', '.post-content', '.entry-content',
                         '.article_content', '.content-detail', '.article-body',
                         '.rich_media_content', '#article-content', '.markdown-body',
                         'main', '.post-body']:
            container = soup.select_one(selector)
            if container:
                text = container.get_text(strip=True)
                if len(text) > 200:
                    return str(container), True

        # 降级：提取所有 <p> 标签
        paragraphs = soup.find_all('p')
        long_paras = [p for p in paragraphs if len(p.get_text(strip=True)) > 30]
        if len(long_paras) >= 3:
            wrapper = soup.new_tag('div')
            for p in long_paras[:50]:
                wrapper.append(p)
            return str(wrapper), True

    except Exception as e:
        logger.debug(f"BS4 extraction failed for {url}: {e}")

    return '', False


def _clean_soup(soup):
    """移除HTML中的无关元素"""
    for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer',
                              'aside', 'iframe', 'noscript', 'form']):
        tag.decompose()
    for tag in soup.find_all(class_=re.compile(
            r'comment|sidebar|widget|share|social|related|recommend|ad-|advertisement', re.I)):
        tag.decompose()


# ========== HN API 专用抓取 ==========

def fetch_hn_api_stories(max_items=30):
    """通过 Firebase API 获取 Hacker News 热门文章"""
    try:
        resp = requests.get(
            'https://hacker-news.firebaseio.com/v0/topstories.json',
            headers=HEADERS, timeout=15
        )
        if resp.status_code != 200:
            return []
        story_ids = resp.json()[:max_items]
    except Exception as e:
        logger.debug(f"HN topstories API failed: {e}")
        return []

    results = []
    for sid in story_ids:
        try:
            r = requests.get(
                f'https://hacker-news.firebaseio.com/v0/item/{sid}.json',
                headers=HEADERS, timeout=10
            )
            if r.status_code != 200:
                continue
            item = r.json()
            if not item or item.get('type') != 'story' or item.get('dead') or item.get('deleted'):
                continue
            title = item.get('title', '')
            url = item.get('url', '') or f"https://news.ycombinator.com/item?id={sid}"
            score = item.get('score', 0)
            if title and len(title) > 4:
                results.append({
                    'title': title,
                    'url': url,
                    'summary': f"Score: {score} | Comments: {item.get('descendants', 0)}",
                })
        except Exception as e:
            logger.debug(f"HN item {sid} failed: {e}")
            continue
    return results


# ========== 三级抓取 ==========

def fetch_html(url, method='get'):
    """获取页面HTML（三级策略）"""
    # 策略1: Scrapling Fetcher
    try:
        from scrapling.fetchers import Fetcher
        fetcher = Fetcher()
        page = fetcher.get(url, impersonate='chrome', timeout=30, headers=HEADERS)
        html = page.body.decode('utf-8', errors='replace')
        if html and len(html) > 500:
            return html
    except Exception as e:
        logger.debug(f"Scrapling failed for {url}: {e}")

    # 策略2: requests 降级
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, verify=False)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        if resp.status_code == 200 and len(resp.text) > 500:
            return resp.text
    except Exception as e:
        logger.debug(f"requests failed for {url}: {e}")

    return None


def extract_articles(html, source):
    """智能内容提取"""
    soup = BeautifulSoup(html, 'lxml')
    base_url = source.url
    results = []
    seen_titles = set()

    # 策略1: 用户配置的CSS选择器
    selectors_str = source.selectors
    if selectors_str:
        try:
            sels = json.loads(selectors_str)
            items = soup.select(sels.get('list', ''))
            for item in items[:50]:
                title_el = item.select_one(sels.get('title', 'a'))
                link_el = item.select_one(sels.get('link', 'a'))
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = ''
                if link_el:
                    href = link_el.get('href', '') or ''
                    if href and not href.startswith('http'):
                        href = urljoin(base_url, href)
                summary_el = item.select_one(sels.get('summary', '')) if sels.get('summary') else None
                summary = summary_el.get_text(strip=True) if summary_el else ''
                if title and len(title) > 4 and title not in seen_titles:
                    seen_titles.add(title)
                    results.append({
                        'title': title, 'url': href, 'summary': summary,
                    })
            if results:
                return results
        except Exception as e:
            logger.debug(f"Selector parsing failed: {e}")

    # 策略2: 列表启发式
    for list_tag in soup.find_all(['ul', 'ol', 'div']):
        links = list_tag.find_all('a', href=True)
        if len(links) < 3:
            continue
        valid_links = []
        for a in links:
            text = a.get_text(strip=True)
            if len(text) >= 10 and text not in seen_titles:
                valid_links.append((text, a.get('href', '')))
        if len(valid_links) >= 3:
            for text, href in valid_links[:30]:
                if href and not href.startswith('http'):
                    href = urljoin(base_url, href)
                if text not in seen_titles:
                    seen_titles.add(text)
                    results.append({'title': text, 'url': href, 'summary': ''})
            if results:
                return results

    # 策略3: 兜底 - 所有 <a> 标签
    EXCLUDE_WORDS = {'首页', '登录', '注册', '更多', 'English', '关于', '联系',
                     '隐私', 'Home', 'Login', 'Sign', 'About', 'Contact', 'More'}
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if (len(text) >= 12 and text not in seen_titles
                and not any(w in text for w in EXCLUDE_WORDS)
                and not re.match(r'^[\d\-/\.]+$', text)):
            href = a['href']
            if not href.startswith('http'):
                href = urljoin(base_url, href)
            seen_titles.add(text)
            results.append({'title': text, 'url': href, 'summary': ''})

    return results[:50]


def crawl_source(source):
    """抓取单个数据源（列表获取 + 正文提取）"""
    from models import db, Article

    # API模式: Hacker News Firebase API
    if source.crawl_method == 'hn_api':
        items = fetch_hn_api_stories(max_items=30)
        if not items:
            source.last_crawl_status = 'error'
            source.last_crawl_at = datetime.utcnow()
            db.session.commit()
            return 0
    else:
        # 标准 HTML 抓取模式
        html = fetch_html(source.url, source.crawl_method)
        if not html:
            source.last_crawl_status = 'error'
            source.last_crawl_at = datetime.utcnow()
            db.session.commit()
            return 0
        items = extract_articles(html, source)

    new_count = 0
    content_count = 0
    for item in items:
        title = item['title']
        content_text = f"{title}{item.get('summary', '')}"
        content_hash = hashlib.sha256(content_text.encode()).hexdigest()

        existing = Article.query.filter_by(content_hash=content_hash).first()
        if existing:
            continue

        cat_name = suggest_category(title, source.category)
        article_url = item.get('url', '')

        # 尝试抓取正文
        article_content = ''
        if article_url and article_url.startswith('http'):
            try:
                article_content, success = fetch_article_content(article_url)
                if success:
                    content_count += 1
            except Exception as e:
                logger.debug(f"正文提取失败 [{title[:30]}]: {e}")

        article = Article(
            source_id=source.id,
            title=title,
            url=article_url,
            summary=item.get('summary', ''),
            content=article_content,
            pub_date=date.today(),
            authority=source.name,
            category_name=cat_name,
            tags=source.category,
            content_hash=content_hash,
        )
        db.session.add(article)
        new_count += 1

        # 正文抓取间隔，避免请求过快
        if article_url and article_url.startswith('http'):
            time.sleep(0.5)

    source.last_crawl_at = datetime.utcnow()
    source.last_crawl_status = 'success'
    db.session.commit()
    logger.info(f"[{source.name}] 新增 {new_count} 条，其中 {content_count} 条含正文")
    return new_count


def crawl_all(app):
    """抓取所有启用的数据源"""
    from models import MonitorSource
    with app.app_context():
        sources = MonitorSource.query.filter_by(enabled=True).all()
        total = 0
        for src in sources:
            try:
                total += crawl_source(src)
            except Exception as e:
                logger.error(f"抓取 {src.name} 失败: {e}")
        logger.info(f"全量抓取完成，共新增 {total} 条")
        return total


def seed_default_sources():
    """预置AI领域数据源"""
    from models import db, MonitorSource
    for src_data in DEFAULT_AI_SOURCES:
        existing = MonitorSource.query.filter_by(url=src_data['url']).first()
        if not existing:
            src = MonitorSource(**src_data)
            db.session.add(src)
    db.session.commit()
