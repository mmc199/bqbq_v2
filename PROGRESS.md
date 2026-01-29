# PROGRESS.md

BQBQ v2 开发进度追踪

## 项目状态

**当前版本**: v2.0.0-alpha
**迁移状态**: 基础功能已完成
**最后更新**: 2026-01-29

## 已完成功能 ✅

### 后端 (FastAPI)

| 功能 | 文件 | 状态 |
|------|------|------|
| 应用入口 | `main.py` | ✅ |
| 配置管理 | `config.py` | ✅ |
| 数据库初始化 | `database.py` | ✅ |
| 图片上传 (FormData) | `main.py` | ✅ |
| 图片 CRUD | `routers/images.py` | ✅ |
| MD5 检查 | `routers/images.py` | ✅ |
| 图片搜索 | `routers/search.py` | ✅ |
| 关键词膨胀 | `routers/search.py` | ✅ |
| 规则树 CRUD | `routers/rules.py` | ✅ |
| CAS 乐观锁 | `routers/rules.py` | ✅ |
| 数据导入 | `routers/system.py` | ✅ |
| 数据导出 | `routers/system.py` | ✅ |
| 系统统计 | `routers/system.py` | ✅ |

### 前端 (Vue 3)

| 组件 | 文件 | 状态 |
|------|------|------|
| 主页面 | `views/Gallery.vue` | ✅ |
| 标签输入 | `components/TagInput.vue` | ✅ |
| 图片卡片 | `components/MemeCard.vue` | ✅ |
| 规则树面板 | `components/RuleTree.vue` | ✅ |
| 规则组节点 | `components/RuleGroupNode.vue` | ✅ |
| 上传模态框 | `components/UploadModal.vue` | ✅ |
| 编辑模态框 | `components/ImageEditModal.vue` | ✅ |
| FAB 按钮组 | `components/FloatingButtons.vue` | ✅ |
| Toast 通知 | `components/ToastContainer.vue` | ✅ |
| API 封装 | `composables/useApi.ts` | ✅ |
| Toast 逻辑 | `composables/useToast.ts` | ✅ |
| 全局状态 | `stores/useGlobalStore.ts` | ✅ |
| 类型定义 | `types/index.ts` | ✅ |

### 基础设施

| 项目 | 状态 |
|------|------|
| Vite 配置 | ✅ |
| Tailwind CSS | ✅ |
| TypeScript 配置 | ✅ |
| 开发代理 | ✅ |
| 本地依赖 (无 CDN) | ✅ |

## 待完成功能 📋

### 高优先级

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 缩略图生成 | 后端生成缩略图，加速加载 | 🔴 高 |
| 图片预览大图 | 点击图片查看原图 | 🔴 高 |
| 数据迁移工具 | 从旧项目导入数据 | 🔴 高 |

### 中优先级

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 批量操作 | 批量删除、批量打标签 | 🟡 中 |
| 拖拽排序 | 规则树拖拽排序 | 🟡 中 |
| 关键词编辑 | 规则树中编辑关键词 | 🟡 中 |
| 无限滚动 | 替代"加载更多"按钮 | 🟡 中 |
| 图片信息面板 | 显示详细元数据 | 🟡 中 |

### 低优先级

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 暗色模式 | 主题切换 | 🟢 低 |
| 快捷键 | 键盘导航 | 🟢 低 |
| PWA 支持 | 离线访问 | 🟢 低 |
| 多语言 | i18n 国际化 | 🟢 低 |

## 已知问题 🐛

| 问题 | 状态 | 备注 |
|------|------|------|
| 暂无已知问题 | - | - |

## 从旧项目迁移清单

### 已迁移

- [x] TagInput 标签输入组件
- [x] 图片卡片展示
- [x] 图片上传 (MD5 去重)
- [x] 图片标签编辑
- [x] 规则树管理
- [x] 关键词膨胀搜索
- [x] 回收站模式
- [x] 数据导入导出
- [x] Toast 通知
- [x] FAB 悬浮按钮

### 待迁移

- [ ] 缩略图服务
- [ ] 图片预览 Lightbox
- [ ] 规则树拖拽排序
- [ ] 冲突检测 UI
- [ ] 临时标签模式

## 版本历史

### v2.0.0-alpha (2026-01-29)

- 🎉 项目初始化
- ✨ 完成基础架构搭建
- ✨ 迁移核心功能
- 📝 创建项目文档

## 下一步计划

1. **测试验证**: 启动前后端，验证所有功能
2. **数据迁移**: 从旧项目导入现有数据
3. **缩略图**: 实现缩略图生成服务
4. **优化**: 根据使用反馈优化 UI/UX
