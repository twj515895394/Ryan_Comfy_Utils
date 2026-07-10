Status: resolved

# 05: requirements.txt 新增 scenedetect 依赖

## 要构建什么

在项目根目录的 `requirements.txt` 中添加 `scenedetect>=0.6` 依赖声明，确保安装本节点包时自动安装 PySceneDetect。

## 验收标准

- [x] `requirements.txt` 存在且包含 `scenedetect>=0.6`
- [x] `pip install -r requirements.txt` 可成功安装

## 被阻塞于

无 - 可以立即开始
