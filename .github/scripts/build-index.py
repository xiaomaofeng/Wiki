#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions: 生成知识库索引 (合并双版本)
同一份报告的MD详细版和HTML简略版合并显示
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

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
    match = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
    if match:
        return match.group(1)
    
    match = re.search(r'(\d{4})[-年]?(\d{1,2})[-月]?(\d{1,2})', filename)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    
    return datetime.now().strftime('%Y-%m-%d')

def extract_summary(content, max_len=200):
    """提取摘要"""
    if content.startswith('---'):
        try:
            _, _, content = content.split('---', 2)
        except:
            pass
    
    text = re.sub(r'#+\s*', '', content)
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'`', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
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
        elif 'healthcare' in path_str:
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

def md_to_html_path(md_relpath):
    """将MD路径转换为对应的HTML路径"""
    html_relpath = md_relpath.replace('.md', '.html')
    
    if html_relpath.startswith('01-research/'):
        return 'pages/' + html_relpath.replace('01-research/', 'research/', 1)
    elif html_relpath.startswith('02-reviews/'):
        return 'pages/' + html_relpath.replace('02-reviews/', 'reviews/', 1)
    
    return 'pages/' + html_relpath

def html_to_md_path(html_relpath):
    """将HTML路径转换为对应的MD路径"""
    md_relpath = html_relpath.replace('.html', '.md')
    
    if md_relpath.startswith('pages/research/'):
        return '01-research/' + md_relpath.replace('pages/research/', '', 1)
    elif md_relpath.startswith('pages/reviews/'):
        return '02-reviews/' + md_relpath.replace('pages/reviews/', '', 1)
    
    return md_relpath.replace('pages/', '')

def scan_reports():
    """扫描所有报告，合并MD和HTML为一条记录"""
    reports = []
    report_id = 1
    
    # 第一步：收集所有MD文件
    md_files = {}  # basename -> {path, content, ...}
    
    for scan_dir in ['01-research', '02-reviews']:
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
                basename = filename.replace('.md', '')
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    md_files[basename] = {
                        'path': relpath,
                        'content': content,
                        'filename': filename
                    }
                except Exception as e:
                    print(f"[错误] 读取MD {filepath}: {e}")
    
    # 第二步：收集所有HTML文件
    html_files = {}  # basename -> {path, content, ...}
    
    if os.path.exists('pages'):
        for root, dirs, files in os.walk('pages'):
            for filename in files:
                if not filename.endswith('.html'):
                    continue
                
                filepath = os.path.join(root, filename)
                relpath = os.path.relpath(filepath).replace('\\', '/')
                basename = filename.replace('.html', '')
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    html_files[basename] = {
                        'path': relpath,
                        'content': content,
                        'filename': filename
                    }
                except Exception as e:
                    print(f"[错误] 读取HTML {filepath}: {e}")
    
    # 第三步：合并为报告记录（以MD为主）
    processed_basenames = set()
    
    # 先处理有MD的报告
    for basename, md_info in md_files.items():
        processed_basenames.add(basename)
        
        content = md_info['content']
        title = extract_title(content, md_info['filename'])
        date = extract_date(content, md_info['filename'])
        summary = extract_summary(content)
        tags = extract_tags(content, title)
        category, subcategory = get_category(md_info['path'])
        
        # 检查是否有对应的HTML
        has_html = basename in html_files
        html_path = html_files[basename]['path'] if has_html else None
        
        # GitHub Pages URL for HTML (直接渲染)
        html_pages_url = f"https://{REPO_OWNER}.github.io/{REPO_NAME}/{html_path}" if has_html else None
        
        report = {
            'id': report_id,
            'title': title,
            'basename': basename,
            'date': date,
            'summary': summary,
            'tags': tags,
            'category': category,
            'subcategory': subcategory,
            'mdPath': md_info['path'],
            'mdGithubUrl': f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{md_info['path']}",
            'hasHtml': has_html,
            'htmlPath': html_path,
            'htmlGithubUrl': f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{html_path}" if has_html else None,
            'htmlPagesUrl': html_pages_url,  # 用于直接渲染HTML
            'versions': ['md'] + (['html'] if has_html else [])
        }
        
        reports.append(report)
        report_id += 1
        
        version_info = "+HTML" if has_html else "MD only"
        print(f"[{version_info}] {title[:40]}...")
    
    # 再处理只有HTML的报告
    for basename, html_info in html_files.items():
        if basename in processed_basenames:
            continue  # 已处理过
        
        content = html_info['content']
        title = extract_title(content, html_info['filename'])
        date = extract_date(content, html_info['filename'])
        summary = extract_summary(content)
        tags = extract_tags(content, title)
        category, subcategory = get_category(html_info['path'])
        
        # GitHub Pages URL for HTML only report
        html_pages_url = f"https://{REPO_OWNER}.github.io/{REPO_NAME}/{html_info['path']}"
        
        report = {
            'id': report_id,
            'title': title,
            'basename': basename,
            'date': date,
            'summary': summary + ' (HTML简略版)',
            'tags': tags,
            'category': category,
            'subcategory': subcategory,
            'mdPath': None,
            'mdGithubUrl': None,
            'hasHtml': True,
            'htmlPath': html_info['path'],
            'htmlGithubUrl': f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{html_info['path']}",
            'htmlPagesUrl': html_pages_url,  # 用于直接渲染HTML
            'versions': ['html']
        }
        
        reports.append(report)
        report_id += 1
        print(f"[HTML only] {title[:40]}...")
    
    return reports

def generate_data_js(reports):
    """生成 data.js"""
    md_only = len([r for r in reports if r['versions'] == ['md']])
    html_only = len([r for r in reports if r['versions'] == ['html']])
    both = len([r for r in reports if 'md' in r['versions'] and 'html'])
    
    data = {
        'lastUpdate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'totalCount': len(reports),
        'mdOnlyCount': md_only,
        'htmlOnlyCount': html_only,
        'bothVersionsCount': both,
        'reports': reports
    }
    
    js_content = f"""// 自动生成于 {data['lastUpdate']}
// 报告总数: {data['totalCount']} 份
// 双版本(MD+HTML): {data['bothVersionsCount']} 份
// 仅MD: {data['mdOnlyCount']} 份
// 仅HTML: {data['htmlOnlyCount']} 份

const REPORTS_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};

if (typeof module !== 'undefined' && module.exports) {{
    module.exports = REPORTS_DATA;
}}
"""
    
    with open('data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"\n[完成] 生成 data.js")
    print(f"  - 总报告数: {len(reports)} 份")
    print(f"  - 双版本(MD+HTML): {both} 份")
    print(f"  - 仅MD: {md_only} 份")
    print(f"  - 仅HTML: {html_only} 份")

def generate_readme(reports):
    """生成 README.md"""
    both = len([r for r in reports if 'md' in r['versions'] and 'html'])
    md_only = len([r for r in reports if r['versions'] == ['md']])
    html_only = len([r for r in reports if r['versions'] == ['html']])
    
    categories = {}
    for r in reports:
        cat = r['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    recent = sorted(reports, key=lambda x: x['date'], reverse=True)[:5]
    
    readme = f"""# 📊 金融研究知识库

> 个人金融研究报告管理系统 | [在线浏览](https://{REPO_OWNER}.github.io/{REPO_NAME}/)

## 📖 双版本说明

同一份报告提供两个版本：

| 版本 | 格式 | 内容特点 | 适用场景 |
|------|------|----------|----------|
| **详细版** | Markdown | 完整分析、数据、逻辑 | 深度研究、编辑修改 |
| **简略版** | HTML | 总结展示、快速阅读 | 快速浏览、分享预览 |

**当前统计**:
- 📄📱 双版本报告: {both} 份
- 📄 仅详细版: {md_only} 份  
- 📱 仅简略版: {html_only} 份

---

## 📈 概览

- **总报告数**: {len(reports)} 份
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

功能：
- 🔍 全文搜索报告
- 📁 按分类筛选
- 🏷️ 按标签浏览
- 📖 选择版本阅读（详细版/简略版）

### 目录结构

```
Wiki/
├── 📄 index.html              # 在线索引入口
├── 📊 data.js                 # 报告索引数据
│
├── 📁 01-research/            # 📄 MD详细版
│   ├── sector/               # 行业研究
│   │   ├── 03-technology/    # TMT科技
│   │   └── 02-healthcare/    # 医疗健康
│   ├── index/                # 指数研究
│   └── ...
│
├── 📁 02-reviews/             # 📄 MD详细版（复盘）
│   └── trade/                # 交易复盘
│
├── 📁 pages/                  # 📱 HTML简略版
│   └── research/
│       ├── sector/           # 行业HTML
│       ├── index/            # 指数HTML
│       └── reviews/          # 复盘HTML
│
├── 📁 03-data/                # 数据资料
└── 📁 04-library/             # 资料库
```

---

## 📑 最新报告

"""
    
    for r in recent:
        versions = []
        if 'md' in r['versions']:
            versions.append("📄 详细版")
        if 'html' in r['versions']:
            versions.append("📱 简略版")
        
        readme += f"""### {r['title']}
- **日期**: {r['date']} | **分类**: {r['category']}
- **版本**: {' | '.join(versions)}
- **标签**: {', '.join(r['tags'][:5])}
- {r['summary'][:100]}...

"""
    
    readme += f"""---

## 📝 添加新报告

### 方式一：添加双版本报告（推荐）
```bash
# 1. 添加MD详细版
cp 报告.md 01-research/sector/03-technology/

# 2. 添加HTML简略版
cp 报告.html pages/research/sector/03-technology/

# 3. 推送（GitHub Actions自动生成索引）
git add . && git commit -m "添加XX报告" && git push
```

### 方式二：仅添加详细版
```bash
cp 报告.md 01-research/sector/XX/
git add . && git commit -m "添加报告" && git push
```

---

## 🔧 自动维护

GitHub Actions 自动执行：
- 自动生成报告索引
- 自动更新 README
- 自动部署 GitHub Pages

**只需推送代码，无需手动操作！**

---

*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme)
    
    print("[完成] 生成 README.md")

def main():
    print("=" * 60)
    print("[构建] 知识库索引 (合并双版本)")
    print("=" * 60)
    
    print("\n[扫描] 合并MD和HTML...\n")
    reports = scan_reports()
    
    if reports:
        print(f"\n[生成] 索引文件...")
        generate_data_js(reports)
        generate_readme(reports)
        print("\n[完成] 构建完成！")
    else:
        print("\n[警告] 未发现报告")
        generate_data_js([])
        generate_readme([])

if __name__ == "__main__":
    main()
