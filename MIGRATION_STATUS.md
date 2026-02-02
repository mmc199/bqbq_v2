# MIGRATION_STATUS (合并汇总)

## 汇总-已完成任务（去重）
- 后端搜索对齐旧版：/api/search 与 /api/search/advanced 基于 images_fts.tags_text，返回 {total, results}；高级搜索字段为 md5/filename/tags/w/h/size/is_trash。
- 标签统计对齐旧版：tags_dict/标签兜底来源改为 images_fts。
- 导入/导出对齐旧版：/api/export/all 使用 tags_text；/api/import/all 直接接收 JSON；导入/导出保留旧 group_id、关键词 is_enabled、COALESCE enabled；层级边表 search_hierarchy_edges 写入/读取并重建闭包表。
- 规则树接口对齐旧版：/api/rules 返回扁平化 version_id/groups/keywords/hierarchy；409 冲突格式对齐；/rules/hierarchy/* 返回 version_id，batch_move 返回 moved/errors 并支持 parent_id=0。
- 规则树构建与缓存对齐：buildRulesTreeFromLegacy 空值兜底、过滤无效 group_id、防 undefined；支持多父层级；304 命中时从本地缓存恢复。
- 规则树写操作对齐旧版：组/关键词增删改查使用旧端点；新建子组后补 hierarchy/add；拖拽/批量移动统一走 batch_move。
- 规则树交互对齐旧版：搜索展开祖先、空名组匹配、批量模式/全选/批量启禁删、拖拽自拖提示/根目录 dropEffect=move、错误日志与提示文案、冲突区 UI 与原因文案。
- 规则树 toast 对齐旧版：新建/启用/禁用/删除/冲突修复/刷新/删除关键词确认与提示，刷新流程包含“正在刷新/已刷新/失败”。
- 规则树 UI 细节：批量工具栏/加载空态 <p>、清空搜索聚焦、触屏下操作按钮可见、图标防缩放。
- 规则树标题布局：按钮紧跟组名显示，不做省略号，依赖横向滚动。
- 规则树图标增强：folder 图标放大并内置子组数量（蓝色）。
- 搜索默认参数对齐旧版：min_tags=0、max_tags=-1；默认不强制附带 trash_bin，非回收站模式前端过滤 trash 图片（backend/app/models/image.py，frontend/src/views/Gallery.vue）。
- 搜索接口统一：前端高级搜索改用 /api/search（由后端自动识别 advanced payload），不再依赖 /api/search/advanced（frontend/src/composables/useApi.ts）。
- 规则树编辑框行为调整：移除组名编辑软删按钮；编辑框不再因失焦自动关闭（避免 F12 选择元素时消失）。
- 缩略图兼容：/thumbnails 支持 trash_bin 子目录回退与原图生成。
- 回收站联动修复：搜索标签规范化，trash 模式与按钮状态同步。
- Gallery/搜索输入对齐：占位文案、TagInput 联想（排除前缀/扩展名提示/最多4条）与规则树关键词合并；加载/到底提示结构与隐藏类对齐旧版。
- MemeCard 对齐：样式与交互、复制按钮绿勾、乐观更新回滚、移除批量打标 pill。
- FAB/面板对齐：排序 data-sort/title、标签数量面板与滑块节奏（最大视觉值 6、-1 表示无限）、临时标签/排序/徽章隐藏类切换。
- Toast 样式对齐旧版：右下角单条、颜色/padding/滑入动画一致。
- 其余编码：全部改动按 UTF-8 读写，修复前端乱码文本。
- 标签编辑逻辑优化：点击标签进入编辑时同步输入框值，避免取消/失焦后标签丢失（frontend/src/components/TagInput.vue，frontend/src/components/MemeCard.vue）。

## 汇总-待处理/剩余差异（去重）
- 继续逐项对照旧版 UI/交互细节（规则树面板动画/边缘交互、其他未覆盖组件）。
- 确认“关键词启用/禁用”在旧版的实际行为（当前前端为 no-op，需决定是否隐藏/禁用或实现旧版等效逻辑）。
- 需要联调验证：规则树批量/拖拽/冲突修复、导入导出、上传与回收站流程。

## 汇总-自检结果（去重）
- 未进行前后端联调测试。
- 本轮修改使用 UTF-8 读写，未发现乱码。

## 分轮记录（整理版）
> 由于已合并清理重复项，分轮记录按主题归并如下（保留主要变更线索）。

### 1) 搜索/导入导出/标签体系
- 搜索与高级搜索对齐旧版字段与响应结构，标签统计改为 images_fts。
- 导入/导出 JSON 与 tags_text 对齐；层级边表写入/读取一致；保留旧 group_id 与 is_enabled。

### 2) 规则树数据与接口
- /api/rules 与 /rules/hierarchy/* 回包格式对齐旧版；parent_id=0 作为根节点。
- buildRulesTreeFromLegacy 兼容旧字段/空值；多父关系与缓存恢复逻辑对齐。

### 3) 规则树交互与 UI
- 批量模式/拖拽/冲突处理/搜索展开与空名组匹配等交互对齐。
- 文案、toast、确认对话、加载/空态 DOM 与旧版一致。
- 触屏操作按钮可见、标题布局按钮紧跟组名、图标防缩放。
- folder 图标放大并在内部显示子组数量（蓝色）。

### 4) Gallery / MemeCard / FAB / Toast
- Gallery 占位、加载/到底提示、隐藏类切换与旧版一致。
- MemeCard 样式与复制绿勾反馈对齐，移除批量打标 pill。
- FAB 面板与排序按钮、标签数量滑块节奏、徽章/面板显示逻辑对齐。
- Toast 样式统一为右下角单条显示。
