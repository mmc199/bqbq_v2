# COMPONENTS.md

前端组件文档

## 组件概览

```
components/
├── TagInput.vue          # 标签输入（核心交互）
├── MemeCard.vue          # 图片卡片
├── RuleTree.vue          # 规则树面板
├── RuleGroupNode.vue     # 规则组节点（递归）
├── UploadModal.vue       # 上传模态框
├── ImageEditModal.vue    # 编辑模态框
├── FloatingButtons.vue   # FAB 悬浮按钮
└── ToastContainer.vue    # Toast 通知容器
```

---

## TagInput.vue

**用途**: 标签胶囊输入组件，支持多种输入方式

**Props**:
| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `Tag[]` | `[]` | 标签数组 (v-model) |
| `placeholder` | `string` | `'添加标签...'` | 占位文本 |
| `theme` | `'blue' \| 'purple' \| 'mixed'` | `'blue'` | 主题色 |
| `enableExcludes` | `boolean` | `false` | 是否启用排除标签 |
| `autoFocus` | `boolean` | `false` | 自动聚焦 |
| `suggestions` | `string[]` | `[]` | 自动补全建议 |

**Events**:
| 名称 | 参数 | 说明 |
|------|------|------|
| `update:modelValue` | `Tag[]` | 标签变化 |
| `submit` | `Tag[]` | 回车提交 |
| `inputUpdate` | `string` | 输入变化 |

**功能**:
- 空格/回车添加标签
- `-tag` 排除标签（红色）
- `tag1,tag2` 同义词组（绿色）
- 点击标签编辑
- Backspace 编辑最后一个标签

---

## MemeCard.vue

**用途**: 图片卡片，显示图片和操作按钮

**Props**:
| 名称 | 类型 | 说明 |
|------|------|------|
| `image` | `MemeImage` | 图片数据 |
| `preferHQ` | `boolean` | 优先加载高清图 |

**Events**:
| 名称 | 参数 | 说明 |
|------|------|------|
| `copy` | `MemeImage` | 复制图片 |
| `delete` | `MemeImage` | 删除图片 |
| `clickTag` | `string` | 点击标签 |
| `edit` | `MemeImage` | 编辑图片 |

**功能**:
- 悬停显示操作按钮
- 下载、复制、删除
- 显示文件信息（格式、尺寸、大小）
- 点击标签添加到搜索

---

## RuleTree.vue

**用途**: 规则树侧边栏面板

**Props**:
| 名称 | 类型 | 说明 |
|------|------|------|
| `visible` | `boolean` | 是否显示 |

**Events**:
| 名称 | 说明 |
|------|------|
| `close` | 关闭面板 |
| `update` | 规则更新 |

**功能**:
- 显示规则树结构
- 搜索过滤
- 新建根组
- 展开/折叠

---

## RuleGroupNode.vue

**用途**: 规则组节点（递归组件）

**Props**:
| 名称 | 类型 | 说明 |
|------|------|------|
| `group` | `RuleGroup` | 规则组数据 |
| `expandedIds` | `Set<number>` | 展开的组 ID |
| `addingGroupParentId` | `number \| null` | 正在添加子组的父 ID |
| `addingKeywordGroupId` | `number \| null` | 正在添加关键词的组 ID |
| `newGroupName` | `string` | 新组名 |
| `newKeyword` | `string` | 新关键词 |

**Events**:
| 名称 | 说明 |
|------|------|
| `toggleExpand` | 切换展开 |
| `startAddGroup` | 开始添加子组 |
| `startAddKeyword` | 开始添加关键词 |
| `deleteGroup` | 删除组 |
| `confirmAddGroup` | 确认添加组 |
| `confirmAddKeyword` | 确认添加关键词 |
| `cancelAdd` | 取消添加 |

---

## UploadModal.vue

**用途**: 图片上传模态框

**Props**:
| 名称 | 类型 | 说明 |
|------|------|------|
| `visible` | `boolean` | 是否显示 |

**Events**:
| 名称 | 说明 |
|------|------|
| `close` | 关闭模态框 |
| `uploaded` | 上传完成 |

**功能**:
- 拖拽上传
- 多文件选择
- MD5 去重检查
- 上传进度显示
- 批量上传

---

## ImageEditModal.vue

**用途**: 图片标签编辑模态框

**Props**:
| 名称 | 类型 | 说明 |
|------|------|------|
| `visible` | `boolean` | 是否显示 |
| `image` | `MemeImage \| null` | 要编辑的图片 |
| `suggestions` | `string[]` | 标签建议 |

**Events**:
| 名称 | 参数 | 说明 |
|------|------|------|
| `close` | - | 关闭模态框 |
| `saved` | `MemeImage` | 保存成功 |

**功能**:
- 显示图片预览
- 编辑标签
- Ctrl+S 快捷保存

---

## FloatingButtons.vue

**用途**: FAB 悬浮按钮组

**Events**:
| 名称 | 参数 | 说明 |
|------|------|------|
| `upload` | - | 打开上传 |
| `openRules` | - | 打开规则树 |
| `export` | - | 导出数据 |
| `import` | - | 导入数据 |
| `toggleTrash` | `boolean` | 切换回收站 |
| `toggleExpansion` | `boolean` | 切换膨胀 |

**功能**:
- 可折叠按钮组
- 上传、规则树、导入导出
- 回收站模式切换
- 关键词膨胀开关

---

## ToastContainer.vue

**用途**: Toast 通知容器

**依赖**: `composables/useToast.ts`

**使用方式**:
```typescript
import { useToast } from '@/composables/useToast'

const toast = useToast()
toast.success('操作成功')
toast.error('操作失败')
toast.info('提示信息')
toast.warning('警告信息')
```

---

## 类型定义

```typescript
// types/index.ts

interface Tag {
  text: string
  exclude: boolean
  synonym: boolean
  synonymWords: string[] | null
}

interface MemeImage {
  id: number
  filename: string
  md5: string
  tags: string
  created_at: string
  file_size?: number
  width?: number
  height?: number
}

interface RuleGroup {
  id: number
  name: string
  keywords: RuleKeyword[]
  children: RuleGroup[]
}

interface RuleKeyword {
  id: number
  keyword: string
  group_id: number
}
```
