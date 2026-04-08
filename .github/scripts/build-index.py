#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions: 生成知识库索引 (支持MD+HTML双版本)
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

# UTF-8输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

REPO_OWNER = "xiaomaofeng"
REPO_NAME = "Wiki"

def extract_title(content, filename):
    """提取标题"""
    # YAML frontmatter
    match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"\'')
    
    # 第一个#标题
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    
    # HTML title标签
    match = re.search(r'<title>(.+?)</title>', content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return Path(filename).stem

def extract_date(content, filename):
    """提取日期"""
    # frontmatter
    match = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
    if match:
        return match.group(1)
    
    # 文件名中的日期
    match = re.search(r'(\d{4})[-年]?(\d{1,2})[-月]?(\d{1,2})', filename)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    
    return datetime.now().strftime('%Y-%m-%d')

def extract_summary(content, max_len=200):
    """提取摘要"""
    # 移除 frontmatter
    if content.startswith('---'):
        try:
            _, _, content = content.split('---', 2)
        except:
            pass
    
    # 清理Markdown标记
    text = re.sub(r'#+\s*', '', content)
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'`', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # 找第一段有意义的文字
    for para in text.split('\n\n'):
        para = para.strip()
        if len(para) > 50:
            return para[:max_len] + '...' if len(para) > max_len else para
    
    return "暂无摘要"

def extract_tags(content, title):
    """提取标签"""
    tags = []
    text = (title + ' ' + content[:3000]).lower()
    
    keywords = {
        '光伏': ['光伏', '太阳能', 'per', '组件', '硅料', '硅片', '515790'],
        'ETF': ['etf', '指数基金'],
        '港股': ['恒生', '港股', '南向资金', '香港'],
        'AI': ['ai', '人工智能', '大模型', 'deepseek'],
        '美联储': ['美联储', '降息', '加息', '货币政策'],
        '医疗': ['医药', '医疗', '创新药', 'cxo', '恒生医疗'],
        '技术分析': ['技术面', '支撑位', '阻力位', 'macd', 'kdj', '均线'],
        '基本面': ['基本面', '景气度', '产能', '供需'],
        '周期': ['周期', '底部', '拐点', '复苏'],
        '策略': ['策略', '操作', '仓位', '止损', '止盈'],
        '新能源': ['新能源', '储能', '风电'],
        '科技': ['科技', '半导体', '芯片', 'tmt'],
        '消费': ['消费', '白酒', '食品饮料', '家电'],
        '金融': ['银行', '券商', '保险', '地产'],
        '投资组合': ['投资组合', '配置', '优化'],
    }
    
    for tag, keywords_list in keywords.items():
        if any(kw in text for kw in keywords_list):
            tags.append(tag)
    
    return tags[:6]

def get_category(path):
    """根据路径获取分类"""
    path_str = str(path).lower()
    
    if 'sector' in path_str:
        if 'consumer' in path_str:
            return ('行业研究', '大消费')
        elif 'healthcare' in path_str or '医疗' in path_str:
            return ('行业研究', '医疗健康')
        elif 'technology' in path_str:
            return ('行业研究', 'TMT科技')
        elif 'manufacturing' in path_str:
            return ('行业研究', '先进制造')
        elif 'cyclical' in path_str:
            return ('行业研究', '周期资源')
        elif 'financial' in path_str:
            return ('行业研究', '金融地产')
        return ('行业研究', '其他行业')
    elif 'index' in path_str:
        return ('指数研究', '指数')
    elif 'company' in path_str:
        return ('个股研究', '个股')
    elif 'macro' in path_str:
        return ('宏观研究', '宏观')
    elif 'strategy' in path_str:
        return ('投资策略', '策略')
    elif 'reviews' in path_str or 'review' in path_str:
        return ('交易复盘', '复盘')
    
    return ('其他', '其他')

def find_html_for_md(md_relpath):
    """查找MD对应的HTML文件"""
    # 将MD路径转换为对应的HTML路径
    # 01-research/sector/... -> pages/research/...
    html_relpath = md_relpath.replace('.md', '.html')
    
    # 处理路径前缀
    if html_relpath.startswith('01-research/'):
        pages_path = 'pages/' + html_relpath.replace('01-research/', 'research/', 1)
    elif html_relpath.startswith('02-reviews/'):
        pages_path = 'pages/' + html_relpath.replace('02-reviews/', 'reviews/', 1)
    else:
        pages_path = 'pages/' + html_relpath
    
    # 统一使用正斜杠并检查
    pages_path = pages_path.replace('\\', '/')
    
    if os.path.exists(pages_path):
        return pages_path
    return None

def scan_md_reports():
    """扫描MD报告（详细版本）"""
    reports = []
    report_id = 1
    
    scan_dirs = ['01-research', '02-reviews']
    
    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
            
        for root, dirs, files in os.walk(scan_dir):
            if '_templates' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.md'):
                    continue
                
                filepath = os.path.join(root, filename)
                relpath = os.path.relpath(filepath).replace('\\', '/')
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    title = extract_title(content, filename)
                    date = extract_date(content, filename)
                    summary = extract_summary(content)
                    tags = extract_tags(content, title)
                    category, subcategory = get_category(relpath)
                    
                    # GitHub URL (MD)
                    github_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{relpath}"
                    
                    # 查找对应的HTML
                    html_path = find_html_for_md(relpath)
                    html_github_url = None
                    if html_path:
                        html_github_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{html_path}"
                    
                    reports.append({
                        'id': report_id,
                        'title': title,
                        'filename': filename,
                        'path': relpath,
                        'githubUrl': github_url,
                        'htmlPath': html_path,
                        'htmlGithubUrl': html_github_url,
                        'hasHtml': html_path is not None,
                        'category': category,
                        'subcategory': subcategory,
                        'date': date,
                        'summary': summary,
                        'tags': tags,
                        'type': 'detailed'
                    })
                    
                    report_id += 1
                    has_html_mark = "+HTML" if html_path else ""
                    print(f"[MD{has_html_mark}] {title[:35]}...")
                    
                except Exception as e:
                    print(f"[错误] {filepath}: {e}")
    
    return reports

def scan_html_only(md_reports):
    """扫描只有HTML的报告（简略版本）"""
    reports = []
    report_id = 1000
    
    if not os.path.exists('pages'):
        return reports
    
    # 获取已有MD的文件名集合（不带扩展名）
    md_basenames = set()
    for r in md_reports:
        basename = r['filename'].replace('.md', '')
        md_basenames.add(basename)
    
    for root, dirs, files in os.walk('pages'):
        for filename in files:
            if not filename.endswith('.html'):
                continue
            
            filepath = os.path.join(root, filename)
            relpath = os.path.relpath(filepath).replace('\\', '/')
            
            # 检查是否有对应的MD文件
            basename = filename.replace('.html', '')
            if basename in md_basenames:
                continue  # 已有MD版本，跳过
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                title = extract_title(content, filename)
                date = extract_date(content, filename)
                summary = extract_summary(content)
                tags = extract_tags(content, title)
                category, subcategory = get_category(relpath)
                
                github_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{relpath}"
                
                reports.append({
                    'id': report_id,
                    'title': title,
                    'filename': filename,
                    'path': relpath,
                    'githubUrl': github_url,
                    'hasHtml': True,
                    'category': category,
                    'subcategory': subcategory,
                    'date': date,
                    'summary': summary + ' (HTML简略版)',
                    'tags': tags,
                    'type': 'summary'
                })
                
                report_id += 1
                print(f"[HTML] {title[:35]}... (仅HTML)")
                
            except Exception as e:
                print(f"[错误] {filepath}: {e}")
    
    return reports

def generate_data_js(all_reports):
    """生成 data.js"""
    md_count = len([r for r in all_reports if r['type'] == 'detailed'])
    html_only_count = len([r for r in all_reports if r['type'] == 'summary'])
    both_count = len([r for r in all_reports if r['type'] == 'detailed' and r['hasHtml']])
    
    data = {
        'lastUpdate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'totalCount': len(all_reports),
        'detailedCount': md_count,
        'summaryCount': html_only_count,
        'bothVersionsCount': both_count,
        'reports': all_reports
    }
    
    js_content = f"""// 自动生成于 {data['lastUpdate']}
// 详细版(MD): {data['detailedCount']} 份
// 仅简略版(HTML): {data['summaryCount']} 份
// 双版本: {data['bothVersionsCount']} 份

const REPORTS_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};

if (typeof module !== 'undefined' && module.exports) {{
    module.exports = REPORTS_DATA;
}}
"""
    
    with open('data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"\n[完成] 生成 data.js")
    print(f"  - MD详细版: {md_count} 份")
    print(f"  - 其中带HTML: {both_count} 份")
    print(f"  - 仅HTML简略版: {html_only_count} 份")

def generate_readme(all_reports):
    """生成 README.md"""
    md_reports = [r for r in all_reports if r['type'] == 'detailed']
    html_only_reports = [r for r in all_reports if r['type'] == 'summary']
    both_count = len([r for r in md_reports if r['hasHtml']])
    
    # 按分类统计
    categories = {}
    for r in all_reports:
        cat = r['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    # 最新报告
    recent = sorted(all_reports, key=lambda x: x['date'], reverse=True)[:5]
    
    readme = f"""# 📊 金融研究知识库

> 个人金融研究报告管理系统 | [在线浏览](https://{REPO_OWNER}.github.io/{REPO_NAME}/)

## 📖 双版本说明

| 版本 | 格式 | 内容 | 用途 |
|------|------|------|------|
| **详细版** | Markdown | 完整分析 | 深度阅读、编辑 |
| **简略版** | HTML | 总结展示 | 快速浏览、分享 |

**当前统计**:
- 📄 MD详细版: {len(md_reports)} 份（其中{both_count}份含HTML简略版）
- 📱 HTML简略版: {len(html_only_reports)} 份（仅HTML）

---

## 📈 概览

- **总报告数**: {len(all_reports)} 份
- **最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

**分类统计**:
"""
    
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        readme += f"- {cat}: {count} 份\n"
    
    readme += f"""
---

## 🚀 快速访问

### 在线索引
👉 **[点击浏览知识库](https://{REPO_OWNER}.github.io/{REPO_NAME}/)**

支持：
- 🔍 全文搜索
- 📁 分类筛选  
- 🏷️ 标签浏览
- 📖 选择阅读版本（详细MD / 简略HTML）

### 目录结构

```
Wiki/
├── 📄 index.html              # 在线索引入口
├── 📊 data.js                 # 索引数据
│
├── 📁 01-research/            # 研究报告（MD详细版）
│   ├── sector/               # 行业研究
│   ├── index/                # 指数研究
│   ├── company/              # 个股研究
│   ├── macro/                # 宏观研究
│   └── strategy/             # 投资策略
│
├── 📁 02-reviews/             # 复盘思考（MD详细版）
│   ├── trade/                # 交易复盘
│   ├── research/             # 研究方法论
│   └── insight/              # 投资随想
│
├── 📁 pages/                  # HTML简略版
│   └── research/
│       ├── sector/           # 行业研究HTML
│       ├── index/            # 指数研究HTML
│       └── ...
│
├── 📁 03-data/                # 数据资料
└── 📁 04-library/             # 资料库
```

---

## 📑 最新报告

"""
    
    for r in recent:
        version_tag = "📄 详细版" if r['type'] == 'detailed' else "📱 简略版"
        readme += f"""### [{r['title']}]({r['path']})
- **日期**: {r['date']} | **分类**: {r['category']} | {version_tag}
- **标签**: {', '.join(r['tags'][:5])}
- {r['summary'][:100]}...

"""
    
    readme += f"""---

## 🔧 自动更新

GitHub Actions 自动维护：
- 自动生成索引
- 自动部署 Pages
- 推送即更新，无需手动操作

---

*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme)
    
    print("[完成] 生成 README.md")

def main():
    print("=" * 60)
    print("[构建] 知识库索引 (MD详细版 + HTML简略版)")
    print("=" * 60)
    
    print("\n[扫描] MD详细版...\n")
    md_reports = scan_md_reports()
    
    print("\n[扫描] HTML简略版（仅HTML的报告）...\n")
    html_only_reports = scan_html_only(md_reports)
    
    all_reports = md_reports + html_only_reports
    
    if all_reports:
        print(f"\n[生成] 索引文件...")
        generate_data_js(all_reports)
        generate_readme(all_reports)
        print("\n[完成] 构建完成！")
    else:
        print("\n[警告] 未发现报告")
        generate_data_js([])
        generate_readme([])

if __name__ == "__main__":
    main()
