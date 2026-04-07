# GitHub Pages 开启步骤

## 1. 访问仓库设置
打开：https://github.com/xiaomaofeng/Wiki/settings/pages

## 2. 配置 Pages
- **Source**: Deploy from a branch
- **Branch**: main / (root)
- 点击 **Save**

## 3. 访问网站
等待 1-2 分钟后访问：
https://xiaomaofeng.github.io/Wiki/

## 4. 后续更新
添加新报告后只需 push 到 main 分支：
```bash
git add .
git commit -m "添加新报告"
git push origin main
```

GitHub Actions 会自动：
- 生成索引 (data.js)
- 更新 README
- 部署 Pages
