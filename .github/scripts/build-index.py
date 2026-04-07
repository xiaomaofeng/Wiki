#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions 用：自动生成知识库索引
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

# 设置UTF-8输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

REPO_NAME = "Wiki"  # 仓库名
REPO_OWNER = "xiaomaofeng"  # 用户名

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
    
    # git 修改时间（备用）
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
        '技术分析': ['技术面', '支撑位', '阻力位', 'macd', 'kdj', '均线'],
        '基本面': ['基本面', '景气度', '产能', '供需'],
        '周期': ['周期', '底部', '拐点', '复苏'],
        '策略': ['策略', '操作', '仓位', '止损', '止盈'],
        '新能源': ['新能源', '储能', '风电'],
        '医药': ['医药', '医疗', '创新药', 'cxo'],
        '科技': ['科技', '半导体', '芯片', 'tmt'],
        '消费': ['消费', '白酒', '食品饮料', '家电'],
        '金融': ['银行', '券商', '保险', '地产'],
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
    elif 'reviews/trade' in path_str:
        return ('交易复盘', '复盘')
    elif 'reviews/insight' in path_str:
        return ('投资随想', '随想')
    
    return ('其他', '其他')

def scan_reports():
    """扫描所有报告"""
    reports = []
    report_id = 1
    
    # 扫描的目录
    scan_dirs = ['01-research', '02-reviews']
    
    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
            
        for root, dirs, files in os.walk(scan_dir):
            # 跳过模板目录
            if '_templates' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.md'):
                    continue
                
                filepath = os.path.join(root, filename)
                relpath = os.path.relpath(filepath)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    title = extract_title(content, filename)
                    date = extract_date(content, filename)
                    summary = extract_summary(content)
                    tags = extract_tags(content, title)
                    category, subcategory = get_category(relpath)
                    
                    # GitHub URL
                    github_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{relpath}"
                    
                    reports.append({
                        'id': report_id,
                        'title': title,
                        'filename': filename,
                        'path': relpath,
                        'githubUrl': github_url,
                        'category': category,
                        'subcategory': subcategory,
                        'date': date,
                        'summary': summary,
                        'tags': tags
                    })
                    
                    report_id += 1
                    print(f"[发现] {title[:40]}...")
                    
                except Exception as e:
                    print(f"[错误] {filepath}: {e}")
    
    return reports

def generate_data_js(reports):
    """生成 data.js"""
    data = {
        'lastUpdate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'totalCount': len(reports),
        'reports': reports
    }
    
    js_content = f"""// 自动生成于 {data['lastUpdate']}
// 报告总数: {data['totalCount']}

const REPORTS_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};

// 兼容导出
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = REPORTS_DATA;
}}
"""
    
    with open('data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"\n[完成] 生成 data.js，共 {len(reports)} 份报告")

def generate_readme(reports):
    """生成 README.md"""
    # 按分类统计
    categories = {}
    for r in reports:
        cat = r['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    # 最新报告
    recent = sorted(reports, key=lambda x: x['date'], reverse=True)[:5]
    
    readme = f"""# 📊 金融研究知识库

> 个人金融研究报告管理系统 | [在线浏览](https://{REPO_OWNER}.github.io/{REPO_NAME}/)

---

## 📈 概览

- **报告总数**: {len(reports)} 份
- **最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- **分类统计**:
"""
    
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        readme += f"  - {cat}: {count} 份\n"
    
    readme += f"""
---

## 🚀 快速访问

### 在线索引
👉 **[点击浏览知识库](https://{REPO_OWNER}.github.io/{REPO_NAME}/)**

支持：
- 🔍 全文搜索
- 📁 分类筛选
- 🏷️ 标签浏览
- 📱 移动端适配

### 目录结构

```
Wiki/
├── 01-research/          # 研究报告
│   ├── sector/           # 行业研究
│   │   ├── 01-consumer/  # 大消费
│   │   ├── 02-healthcare/# 医疗健康
│   │   ├── 03-technology/# TMT科技
│   │   ├── 04-manufacturing/ # 先进制造
│   │   ├── 05-cyclical/  # 周期资源
│   │   └── 06-financial/ # 金融地产
│   ├── index/            # 指数研究
│   ├── company/          # 个股研究
│   ├── macro/            # 宏观研究
│   └── strategy/         # 投资策略
├── 02-reviews/           # 复盘思考
│   ├── trade/            # 交易复盘
│   ├── research/         # 研究方法论
│   └── insight/          # 投资随想
├── 03-data/              # 数据资料
└── 04-library/           # 资料库
```

---

## 📑 最新报告

"""
    
    for r in recent:
        readme += f"""### [{r['title']}]({r['path']})
- **日期**: {r['date']} | **分类**: {r['category']} - {r['subcategory']}
- **标签**: {', '.join(r['tags'])}
- {r['summary'][:100]}...

"""
    
    readme += f"""---

## 🔧 自动更新

本知识库使用 GitHub Actions 自动维护：
- 推送新报告后自动生成索引
- 自动更新在线浏览页面
- 无需手动运行脚本

---

*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme)
    
    print("[完成] 生成 README.md")

def main():
    print("=" * 60)
    print("[构建] 知识库索引")
    print("=" * 60)
    
    print("\n[扫描] 报告...\n")
    reports = scan_reports()
    
    if reports:
        print(f"\n[生成] 索引文件...")
        generate_data_js(reports)
        generate_readme(reports)
        print("\n[完成] 构建完成！")
    else:
        print("\n[警告] 未发现报告")
        # 仍然生成空文件
        generate_data_js([])
        generate_readme([])

if __name__ == "__main__":
    main()
