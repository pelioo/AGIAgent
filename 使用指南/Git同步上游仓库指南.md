# Git 同步上游仓库指南

本文档介绍如何从上游主仓库拉取更新并合并到你的仓库。

---

## 仓库配置说明

| 仓库 | 地址 | 说明 |
|------|------|------|
| **upstream** | https://github.com/agi-hub/AGIAgent | 上游主仓库（你分支的来源） |
| **origin** | https://github.com/pelioo/AGIAgent | 你的远程仓库 |

---

## 同步步骤

### 第一步：拉取上游更新

```bash
git fetch upstream
```

**作用**：从上游仓库下载最新的代码和提交记录，但不会修改你的本地代码。

---

### 第二步：查看上游更新内容

查看上游 main 分支有哪些新提交：

```bash
git log HEAD..upstream/main --oneline
```

查看具体修改了哪些文件：

```bash
git diff HEAD..upstream/main --stat
```

---

### 第三步：合并上游更新

切换到你的主分支并合并上游更新：

```bash
git checkout main
git merge upstream/main
```

**说明**：
- 如果没有冲突，Git 会自动合并
- 如果有冲突，Git 会提示你手动解决冲突

---

### 第四步：推送到你的远程仓库

```bash
git push origin main
```

**作用**：将合并后的结果上传到你的 GitHub 仓库。

---

## 完整命令汇总

```bash
# 一行命令（确保在 main 分支）
git fetch upstream && git checkout main && git merge upstream/main && git push origin main
```

或者分步执行：

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

---

## 冲突处理

如果合并时出现冲突，Git 会暂停并提示你解决冲突。

### 解决冲突的步骤：

1. **查看冲突文件**：
   ```bash
   git status
   ```

2. **手动编辑冲突文件**，保留你需要的代码

3. **标记冲突已解决**：
   ```bash
   git add <冲突文件>
   ```

4. **完成合并提交**：
   ```bash
   git commit
   ```

5. **推送到远程**：
   ```bash
   git push origin main
   ```

---

## 常见问题

### Q: 如何查看当前有哪些远程仓库？

```bash
git remote -v
```

### Q: 如何查看本地分支和上游分支的差异？

```bash
git log HEAD..upstream/main --oneline
```

### Q: 如果想撤销合并怎么办？

```bash
git merge --abort
```

---

## 相关文件位置

| 文件 | 说明 |
|------|------|
| `.git/config` | Git 配置文件，包含远程仓库信息 |
| `GUI/auth_manager.py` | 认证逻辑 |
| `GUI/templates/register.html` | 注册页面 |

---

## 修改记录

| 日期 | 修改内容 |
|------|----------|
| 2026-03-16 | 初始文档 |
