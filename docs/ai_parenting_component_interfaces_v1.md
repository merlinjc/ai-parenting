# 18—48个月幼儿家长辅助型 AI 产品：通用组件接口定义 V1

## 一、文档目标

本稿承接《关键页面组件拆解 V1》中定义的 9 个通用组件和《数据结构草案 V1》中的领域对象字段定义，目的是把组件拆解中以自然语言描述的"输入、输出、状态依赖"推进到**可直接对照编码的伪类型签名**。换句话说，本稿要回答的核心问题是：**每个通用组件的 Props / Protocol 长什么样、接受什么类型的数据、回调什么类型的事件、需要从哪一级状态中读取依赖。**

之所以在数据结构草案和 AI 输出结构之后做这一步，而不是直接进入代码实现，是因为通用组件是所有页面组件区的底层积木。如果这 9 块积木的接口定义不稳定，上层 30+ 组件区实例的开发就会频繁返工。先把接口固定，再进入组件库代码实现或高保真设计，可以确保设计与工程在同一套契约上对齐。

本稿同时提供 **TypeScript** 和 **Swift Protocol** 两套伪类型签名。TypeScript 签名适用于 React / React Native / Flutter（Dart 可按此推导）开发；Swift Protocol 签名适用于 SwiftUI 原生开发。两套签名保持字段名称和语义一致，仅在语言惯例上有差异（如命名风格、可选语法）。

| 本稿解决的问题 | 本稿暂不展开的问题 |
|---|---|
| 固定 9 个通用组件的接口类型签名 | 组件内部视觉实现与动效细节 |
| 明确每个 Props 字段的来源领域对象 | 具体组件库代码、单元测试与构建配置 |
| 统一回调事件的命名与参数结构 | 状态管理框架选型（Redux / Combine / Provider 等） |
| 为跨平台实现提供双语参照 | 平台特定适配（键盘弹出、安全区等） |
| 关联数据结构草案的字段到组件 Props | 网络层、缓存层与数据同步策略 |

## 二、接口定义的设计约定

在进入具体组件之前，先固定几条贯穿全部签名的约定，确保 9 个组件的接口风格一致。

**第一，Props 字段名与领域对象字段名保持一致。** 如果组件接收的数据来自 Plan 对象的 title 字段，Props 中就使用 planTitle 或 plan_title（视语言惯例），不另起别名。这样做的好处是：工程师看到 Props 字段就知道该去哪个 API 响应中取值。

**第二，回调事件统一采用 on + 动词 + 名词 的命名方式。** 例如 onTagTap、onButtonPress、onSelectionChange。回调参数应传递必要的标识信息（如 ID、索引），不传递 UI 层细节（如坐标、手势对象）。

**第三，区分必填与可选。** TypeScript 中通过 `?` 标记可选；Swift 中通过 `Optional` 或默认参数标记。必填字段意味着组件在没有该数据时无法正常渲染；可选字段意味着组件在缺少该数据时降级为更简态。

**第四，枚举类型保持与数据结构草案一致。** 例如 CompletionStatus 的取值必须与 DayTask.completion_status 的 Enum 定义完全对齐，不额外增减选项。

**第五，组件内部状态不暴露为 Props。** 如 TimelineList 的分页加载状态、InputFormSection 的当前输入值，这些是组件自行管理的内部状态，不出现在 Props 接口中。组件通过回调事件将结果传递给父组件。

| 约定 | 具体要求 |
|---|---|
| **字段名与领域对象一致** | Props 字段可追溯到 API 响应中的具体路径 |
| **回调命名规则** | on + 动词 + 名词，参数传标识不传 UI 细节 |
| **必填与可选区分** | TS 用 `?`，Swift 用 `Optional` |
| **枚举一致性** | 与数据结构草案中的 Enum 定义完全对齐 |
| **内部状态不暴露** | 分页、输入值等内部状态由组件自管 |

## 三、通用类型定义

以下类型被多个组件共享，提前统一定义。

### 3.1 TypeScript 通用类型

```typescript
// ——— 枚举类型（与数据结构草案对齐） ———

type AgeStage = '18_24m' | '24_36m' | '36_48m';

type RiskLevel = 'normal' | 'attention' | 'consult';

type FocusTheme = 'language' | 'social' | 'emotion' | 'motor' | 'cognition' | 'self_care';

type CompletionStatus = 'pending' | 'executed' | 'partial' | 'needs_record';

type MessageType = 'plan_reminder' | 'record_prompt' | 'weekly_feedback_ready' | 'risk_alert' | 'system';

type DecisionValue = 'continue' | 'lower_difficulty' | 'change_focus';

type RecordType = 'quick_check' | 'event' | 'voice';

type SelectionMode = 'single' | 'multiple';

// ——— 样式枚举 ———

type TagStyle = 'emphasis' | 'normal';

type ButtonLevel = 'primary' | 'secondary' | 'tertiary';

// ——— 基础数据结构 ———

interface TagItem {
  id: string;
  text: string;
  style: TagStyle;
}

interface ButtonItem {
  id: string;
  text: string;
  level: ButtonLevel;
  action: string;            // 动作标识，由父组件解释
  disabled?: boolean;
  loading?: boolean;
}

interface IconButtonItem {
  id: string;
  icon: string;              // 图标资源标识
  action: string;
  badgeCount?: number;       // 未读徽标数（0 或 undefined 时不显示）
}

interface TimelineEntry {
  id: string;
  timestamp: string;         // ISO 8601 格式
  title: string;
  description?: string;
  targetPage?: string;       // 深链目标页标识
  targetParams?: Record<string, string>;
}

interface SelectableTag {
  id: string;
  text: string;
  defaultSelected?: boolean;
}

interface InputFieldConfig {
  id: string;
  type: 'text' | 'tag_select' | 'voice' | 'textarea' | 'scene_select' | 'theme_select';
  label: string;
  placeholder?: string;
  required?: boolean;
  options?: Array<{ id: string; text: string }>;  // tag_select / scene_select / theme_select 使用
  maxLength?: number;
}

interface ColumnContent {
  title: string;
  body: string;
}
```

### 3.2 Swift 通用类型

```swift
// ——— 枚举类型（与数据结构草案对齐） ———

enum AgeStage: String, Codable {
    case m18_24 = "18_24m"
    case m24_36 = "24_36m"
    case m36_48 = "36_48m"
}

enum RiskLevel: String, Codable {
    case normal, attention, consult
}

enum FocusTheme: String, Codable {
    case language, social, emotion, motor, cognition, selfCare = "self_care"
}

enum CompletionStatus: String, Codable {
    case pending, executed, partial, needsRecord = "needs_record"
}

enum MessageType: String, Codable {
    case planReminder = "plan_reminder"
    case recordPrompt = "record_prompt"
    case weeklyFeedbackReady = "weekly_feedback_ready"
    case riskAlert = "risk_alert"
    case system
}

enum DecisionValue: String, Codable {
    case `continue`, lowerDifficulty = "lower_difficulty", changeFocus = "change_focus"
}

enum RecordType: String, Codable {
    case quickCheck = "quick_check", event, voice
}

enum SelectionMode {
    case single, multiple
}

// ——— 样式枚举 ———

enum TagStyle {
    case emphasis, normal
}

enum ButtonLevel {
    case primary, secondary, tertiary
}

// ——— 基础数据结构 ———

struct TagItem: Identifiable {
    let id: String
    let text: String
    let style: TagStyle
}

struct ButtonItem: Identifiable {
    let id: String
    let text: String
    let level: ButtonLevel
    let action: String
    var isDisabled: Bool = false
    var isLoading: Bool = false
}

struct IconButtonItem: Identifiable {
    let id: String
    let icon: String
    let action: String
    var badgeCount: Int = 0
}

struct TimelineEntry: Identifiable {
    let id: String
    let timestamp: Date
    let title: String
    var description: String?
    var targetPage: String?
    var targetParams: [String: String]?
}

struct SelectableTag: Identifiable {
    let id: String
    let text: String
    var defaultSelected: Bool = false
}

struct InputFieldConfig: Identifiable {
    let id: String
    let type: InputFieldType
    let label: String
    var placeholder: String?
    var isRequired: Bool = false
    var options: [SelectOption]?
    var maxLength: Int?
}

enum InputFieldType {
    case text, tagSelect, voice, textarea, sceneSelect, themeSelect
}

struct SelectOption: Identifiable {
    let id: String
    let text: String
}

struct ColumnContent {
    let title: String
    let body: String
}
```

## 四、StatusTagGroup（状态标签组）

状态标签组是纯展示组件，用于横向排列展示当前阶段、主题、风险层级等分类标签。它不维护内部状态，所有数据由外部传入。

**典型使用场景：** 首页 H-2 FocusCard 中展示阶段 + 主题 + 状态级别标签；即时求助 A-3 ContextCard 中展示上下文标签。

### 4.1 TypeScript 接口

```typescript
interface StatusTagGroupProps {
  /** 标签数组，按传入顺序横向排列 */
  tags: TagItem[];

  /** 标签点击事件（可选，仅用于跳转场景，不用于选中） */
  onTagTap?: (tagId: string) => void;

  /** 是否允许横向滚动溢出（默认 true，窄屏防止截断） */
  scrollable?: boolean;
}
```

### 4.2 Swift Protocol

```swift
protocol StatusTagGroupView: View {
    var tags: [TagItem] { get }
    var onTagTap: ((String) -> Void)? { get }
    var isScrollable: Bool { get }
}

// SwiftUI 实现签名示例
struct StatusTagGroup: View {
    let tags: [TagItem]
    var onTagTap: ((String) -> Void)? = nil
    var isScrollable: Bool = true
    
    var body: some View { /* ... */ }
}
```

### 4.3 数据来源映射

| Props 字段 | 数据来源 | 典型取值路径 |
|---|---|---|
| tags[0] (阶段标签) | Child.stage | `GET /home/summary` → child.stage → 映射为 TagItem |
| tags[1] (主题标签) | Plan.focus_theme 或 Child.focus_themes | `GET /home/summary` → active_plan.focus_theme |
| tags[2] (状态标签) | Child.risk_level | `GET /home/summary` → child.risk_level |

## 五、ActionButtonGroup（动作按钮组）

动作按钮组是系统中使用最频繁的交互组件，在几乎所有卡片和面板的底部都有出现。它支持一个主按钮和零至两个次级按钮的组合。

**典型使用场景：** FocusCard 底部的"查看本周计划""查看阶段说明"；TodayTaskCard 底部的"去执行"；CompletionPanel 中的"完成后去记录""现在求助"。

### 5.1 TypeScript 接口

```typescript
interface ActionButtonGroupProps {
  /** 按钮数组，按传入顺序排列（第一个通常为 primary） */
  buttons: ButtonItem[];

  /** 按钮点击事件，参数为按钮的 action 标识 */
  onButtonPress: (action: string) => void;

  /** 布局方向（默认 horizontal） */
  layout?: 'horizontal' | 'vertical';

  /** 按钮之间的间距（逻辑像素，默认 12） */
  spacing?: number;
}
```

### 5.2 Swift Protocol

```swift
struct ActionButtonGroup: View {
    let buttons: [ButtonItem]
    let onButtonPress: (String) -> Void
    var layout: ButtonGroupLayout = .horizontal
    var spacing: CGFloat = 12
    
    var body: some View { /* ... */ }
}

enum ButtonGroupLayout {
    case horizontal, vertical
}
```

### 5.3 数据来源映射

ActionButtonGroup 的 buttons 数组通常由各页面组件区根据当前状态动态构建，而非直接从 API 响应中获取。例如：

| 使用场景 | 按钮构建逻辑 |
|---|---|
| H-2 FocusCard | 始终展示"查看本周计划"（primary）+ 可选"查看阶段说明"（secondary） |
| H-3 TodayTaskCard | completion_status == pending 时展示"去执行"（primary）；== executed 时展示"已完成"（disabled） |
| P-5 CompletionPanel | 始终展示"完成后去记录"（primary）+ "现在求助"（secondary） |
| A-5 FollowUpActionBar | 由 InstantHelpResult 的 suggest_* 字段动态决定按钮可见性 |

## 六、SummaryCard（信息摘要卡）

信息摘要卡是系统中最通用的信息展示容器，承担"在有限空间内传达单一主题核心信息"的职责。它可以包含标题、副标题、正文、标签组和动作按钮组。

**典型使用场景：** 首页 H-4 RecentRecordSummary、H-5 PendingReturnCard、H-6 QuickHelpEntry；周反馈 F-2 PositiveChangeCard、F-3 OpportunityCard、F-5 ConservativePathNote。

### 6.1 TypeScript 接口

```typescript
interface SummaryCardProps {
  /** 卡片标题 */
  title: string;

  /** 副标题（可选） */
  subtitle?: string;

  /** 正文摘要 */
  body?: string;

  /** 嵌入的标签组（可选，展示在标题下方） */
  tags?: TagItem[];

  /** 嵌入的按钮组（可选，展示在正文下方） */
  buttons?: ButtonItem[];

  /** 卡片整体点击事件（可选，与按钮事件互不冲突） */
  onCardTap?: () => void;

  /** 按钮点击事件（当 buttons 不为空时必须提供） */
  onButtonPress?: (action: string) => void;

  /** 未读 / 已完成标记（可选） */
  badge?: 'unread' | 'completed' | 'attention' | null;

  /** 卡片边框样式（默认 solid） */
  borderStyle?: 'solid' | 'dashed';

  /** 是否展示支撑证据摘要区（周反馈场景使用） */
  evidenceText?: string;
}
```

### 6.2 Swift Protocol

```swift
struct SummaryCard: View {
    let title: String
    var subtitle: String? = nil
    var bodyText: String? = nil       // 注意：避免与 View.body 计算属性命名冲突
    var tags: [TagItem]? = nil
    var buttons: [ButtonItem]? = nil
    var onCardTap: (() -> Void)? = nil
    var onButtonPress: ((String) -> Void)? = nil
    var badge: CardBadge? = nil
    var borderStyle: CardBorderStyle = .solid
    var evidenceText: String? = nil
    
    var body: some View { /* ... */ }
}

enum CardBadge {
    case unread, completed, attention
}

enum CardBorderStyle {
    case solid, dashed
}
```

### 6.3 数据来源映射

| 使用场景 | title 来源 | body 来源 | 特殊配置 |
|---|---|---|---|
| H-4 RecentRecordSummary | "最近记录" (固定) | `GET /home/summary` → recent_records[0].content | badge: synced_to_plan ? .completed : nil |
| H-5 PendingReturnCard | `GET /home/summary` → pending_messages[0].type 映射 | pending_messages[0].summary | onCardTap → 深链到 target_page |
| F-2 PositiveChangeCard | WeeklyFeedback.positive_changes[n].title | positive_changes[n].description | evidenceText: positive_changes[n].supporting_evidence |
| F-5 ConservativePathNote | "如果这周比较困难" (固定) | WeeklyFeedback.conservative_path_note | borderStyle: .dashed |

## 七、SplitInfoPanel（双列信息区）

双列信息区用于并排展示两类相关但独立的信息，最典型的场景是"主练习"与"自然嵌入"的并列展示。

**典型使用场景：** 首页 H-3 TodayTaskCard 中的主练习/自然嵌入摘要；计划页 P-4 DailyTaskPanel 中的主练习/自然嵌入详情。

### 7.1 TypeScript 接口

```typescript
interface SplitInfoPanelProps {
  /** 左列内容 */
  leftColumn: ColumnContent;

  /** 右列内容 */
  rightColumn: ColumnContent;

  /** 左列点击事件（可选） */
  onLeftColumnTap?: () => void;

  /** 右列点击事件（可选） */
  onRightColumnTap?: () => void;

  /** 窄屏回退模式（默认 stack，将双列变为上下堆叠） */
  narrowFallback?: 'stack' | 'scroll';
}
```

### 7.2 Swift Protocol

```swift
struct SplitInfoPanel: View {
    let leftColumn: ColumnContent
    let rightColumn: ColumnContent
    var onLeftColumnTap: (() -> Void)? = nil
    var onRightColumnTap: (() -> Void)? = nil
    var narrowFallback: NarrowFallbackMode = .stack
    
    var body: some View { /* ... */ }
}

enum NarrowFallbackMode {
    case stack, scroll
}
```

### 7.3 数据来源映射

| 使用场景 | leftColumn 来源 | rightColumn 来源 |
|---|---|---|
| H-3 TodayTaskCard | DayTask.main_exercise_title + 截断摘要 | DayTask.natural_embed_title + 截断摘要 |
| P-4 DailyTaskPanel | DayTask.main_exercise_title + main_exercise_description | DayTask.natural_embed_title + natural_embed_description |

## 八、TimelineList（时间线列表）

时间线列表是系统中最长的内容展示组件，按时间倒序排列条目，支持分页加载。组件内部管理分页状态，通过回调请求更多数据。

**典型使用场景：** 记录页 R-5 RecordTimeline；消息中心 M-2 MessageList。

### 8.1 TypeScript 接口

```typescript
interface TimelineListProps {
  /** 条目数组（已排序，由父组件保证时间倒序） */
  entries: TimelineEntry[];

  /** 是否还有更多数据可加载 */
  hasMore: boolean;

  /** 请求加载更多数据（滚动到底部时触发） */
  onLoadMore: () => void;

  /** 条目点击事件 */
  onEntryTap: (entryId: string) => void;

  /** 是否正在加载更多（控制底部加载指示器） */
  isLoadingMore?: boolean;

  /** 空态提示文本（entries 为空时展示） */
  emptyText?: string;

  /** 时间分组方式（默认 byDay，按日期分组显示分隔线） */
  groupBy?: 'byDay' | 'byWeek' | 'none';
}
```

### 8.2 Swift Protocol

```swift
struct TimelineList: View {
    let entries: [TimelineEntry]
    let hasMore: Bool
    let onLoadMore: () -> Void
    let onEntryTap: (String) -> Void
    var isLoadingMore: Bool = false
    var emptyText: String = "暂无记录"
    var groupBy: TimelineGroupMode = .byDay
    
    var body: some View { /* ... */ }
}

enum TimelineGroupMode {
    case byDay, byWeek, none
}
```

### 8.3 数据来源映射

| 使用场景 | entries 来源 | hasMore 来源 | onLoadMore 触发 |
|---|---|---|---|
| R-5 RecordTimeline | `GET /records?limit=20&before={cursor}` → records 映射为 TimelineEntry | 响应中的 has_more | 调用下一页 cursor |
| M-2 MessageList | `GET /messages?limit=20&before={cursor}` → messages 映射为 TimelineEntry | 响应中的 has_more | 调用下一页 cursor |

## 九、BottomTabBar（底部导航栏）

底部导航栏固定在屏幕底部，提供首页、计划、记录三个主 Tab 的切换入口。它是全局级组件，存在于所有三个主任务页面。

**典型使用场景：** 首页 H-7、计划页 P-7、记录页 R-6。

### 9.1 TypeScript 接口

```typescript
interface TabItem {
  id: string;
  icon: string;
  activeIcon: string;        // 激活态图标（可能与默认态不同）
  label: string;
  targetPage: string;
}

interface BottomTabBarProps {
  /** Tab 配置数组（固定 3 个：首页、计划、记录） */
  tabs: TabItem[];

  /** 当前激活的 Tab ID */
  activeTabId: string;

  /** Tab 切换事件 */
  onTabSwitch: (tabId: string) => void;
}
```

### 9.2 Swift Protocol

```swift
struct TabItem: Identifiable {
    let id: String
    let icon: String
    let activeIcon: String
    let label: String
    let targetPage: String
}

struct BottomTabBar: View {
    let tabs: [TabItem]
    let activeTabId: String
    let onTabSwitch: (String) -> Void
    
    var body: some View { /* ... */ }
}
```

### 9.3 数据来源映射

BottomTabBar 的 tabs 配置为客户端静态定义，不从 API 获取。activeTabId 由前台路由状态（全局级 Navigation 状态）驱动。

| Tab | id | label | targetPage |
|---|---|---|---|
| 首页 | home | 首页 | /home |
| 计划 | plan | 计划 | /plan |
| 记录 | record | 记录 | /record |

## 十、TopToolBar（顶部工具栏）

顶部工具栏位于页面顶部，包含页面标题、可选副标题和右侧图标按钮组。它在不同页面中展示不同的标题内容，但结构保持统一。

**典型使用场景：** 首页 H-1（展示儿童昵称和月龄）；计划页 P-1（展示"本周计划"）；消息中心 M-1。

### 10.1 TypeScript 接口

```typescript
interface TopToolBarProps {
  /** 页面标题 */
  title: string;

  /** 副标题（可选，如月龄信息） */
  subtitle?: string;

  /** 右侧图标按钮数组 */
  rightButtons?: IconButtonItem[];

  /** 图标按钮点击事件 */
  onIconButtonPress?: (action: string) => void;

  /** 是否展示返回按钮（非根页面时为 true） */
  showBackButton?: boolean;

  /** 返回按钮点击事件 */
  onBackPress?: () => void;
}
```

### 10.2 Swift Protocol

```swift
struct TopToolBar: View {
    let title: String
    var subtitle: String? = nil
    var rightButtons: [IconButtonItem]? = nil
    var onIconButtonPress: ((String) -> Void)? = nil
    var showBackButton: Bool = false
    var onBackPress: (() -> Void)? = nil
    
    var body: some View { /* ... */ }
}
```

### 10.3 数据来源映射

| 使用场景 | title 来源 | subtitle 来源 | rightButtons 配置 |
|---|---|---|---|
| 首页 H-1 | Child.nickname | "\(Child.age_months)个月" | 消息入口(badgeCount=unread_count) + 档案入口 |
| 计划页 P-1 | "本周计划" (固定) | Plan.title | 无 |
| 消息中心 M-1 | "消息" (固定) | 无 | 无 |
| 即时求助 A-1 | "现在怎么办" (固定) | 无 | 无（showBackButton=true） |
| 周反馈 F-1 | "本周反馈" (固定) | 无 | 无（showBackButton=true） |

## 十一、InputFormSection（输入表单区）

输入表单区是记录页和即时求助页的核心交互组件，支持多种输入类型的动态组合。组件内部管理当前输入状态和校验状态，通过回调将结果传出。

**典型使用场景：** 记录页 R-3 EventRecordForm；记录页 R-4 VoiceInputSection（语音输入模式）；即时求助 A-2 ScenarioInputPanel。

### 11.1 TypeScript 接口

```typescript
interface FormValues {
  [fieldId: string]: string | string[] | null;  // 文本值或选中项ID数组
}

interface FormValidation {
  isValid: boolean;
  errors: { [fieldId: string]: string };         // 字段级错误信息
}

interface InputFormSectionProps {
  /** 输入项配置数组（按传入顺序排列） */
  fields: InputFieldConfig[];

  /** 值变更事件（每次任意字段变化时触发，传递完整当前值） */
  onValuesChange: (values: FormValues) => void;

  /** 提交事件（提交按钮点击或键盘完成时触发） */
  onSubmit: (values: FormValues) => void;

  /** 初始值（可选，用于编辑场景或从其他页面预填） */
  initialValues?: FormValues;

  /** 提交按钮文本（默认"提交"） */
  submitButtonText?: string;

  /** 是否正在提交（控制提交按钮加载状态） */
  isSubmitting?: boolean;

  /** 语音录入完成回调（仅当 fields 中包含 voice 类型时有效） */
  onVoiceRecorded?: (audioBlob: any) => void;

  /** 外部校验错误（服务端返回的错误可通过此字段注入） */
  externalErrors?: { [fieldId: string]: string };
}
```

### 11.2 Swift Protocol

```swift
typealias FormValues = [String: FormFieldValue]

enum FormFieldValue {
    case text(String)
    case selection([String])   // 选中项 ID 数组
    case empty
}

struct FormValidationError: Identifiable {
    let id: String             // fieldId
    let message: String
}

struct InputFormSection: View {
    let fields: [InputFieldConfig]
    let onValuesChange: (FormValues) -> Void
    let onSubmit: (FormValues) -> Void
    var initialValues: FormValues? = nil
    var submitButtonText: String = "提交"
    var isSubmitting: Bool = false
    var onVoiceRecorded: ((Data) -> Void)? = nil
    var externalErrors: [String: String]? = nil
    
    var body: some View { /* ... */ }
}
```

### 11.3 数据来源映射

| 使用场景 | fields 配置 | initialValues 来源 | onSubmit 目标 |
|---|---|---|---|
| R-3 EventRecordForm | text(content) + sceneSelect(scene) + themeSelect(theme) + tagSelect(time_of_day) | 从计划页跳转时预填 source_plan_id 关联的 theme | `POST /records` |
| R-4 VoiceInputSection | voice(audio) | 无 | `POST /records/voice/upload-url` → 上传 → `POST /records` |
| A-2 ScenarioInputPanel | tagSelect(scenario) + textarea(input_text) | 无 | `POST /ai/instant-help` |

## 十二、SelectableTagGroup（可选中标签组）

可选中标签组与 StatusTagGroup 外观相似，但支持单选或多选交互。选中状态由组件内部管理，通过回调通知父组件当前选中集合。

**典型使用场景：** 记录页 R-2 QuickCheckPanel（多选打点）；周反馈 F-4 NextWeekDecisionPanel（单选决策）；计划页 P-5 CompletionPanel 的完成状态选择（单选）。

### 12.1 TypeScript 接口

```typescript
interface SelectableTagGroupProps {
  /** 标签选项数组 */
  tags: SelectableTag[];

  /** 选择模式 */
  mode: SelectionMode;

  /** 选中变更事件（返回当前所有选中标签的 ID 数组） */
  onSelectionChange: (selectedIds: string[]) => void;

  /** 是否允许取消所有选中（单选模式下默认 false，多选模式下默认 true） */
  allowEmpty?: boolean;

  /** 标签排列方向（默认 wrap，自动换行） */
  layout?: 'wrap' | 'horizontal-scroll';

  /** 是否禁用交互（用于已决策不可更改的场景） */
  disabled?: boolean;
}
```

### 12.2 Swift Protocol

```swift
struct SelectableTagGroup: View {
    let tags: [SelectableTag]
    let mode: SelectionMode
    let onSelectionChange: ([String]) -> Void
    var allowEmpty: Bool? = nil       // nil 时根据 mode 自动推断
    var layout: TagGroupLayout = .wrap
    var isDisabled: Bool = false
    
    var body: some View { /* ... */ }
}

enum TagGroupLayout {
    case wrap, horizontalScroll
}
```

### 12.3 数据来源映射

| 使用场景 | tags 来源 | mode | onSelectionChange 目标 |
|---|---|---|---|
| R-2 QuickCheckPanel | Plan.observation_candidates 映射为 SelectableTag | multiple | 选中结果暂存页面状态，提交时作为 Record.tags |
| F-4 NextWeekDecisionPanel | WeeklyFeedback.decision_options 映射为 SelectableTag | single | `POST /weekly-feedbacks/{id}/decision` |
| P-5 CompletionPanel | CompletionStatus 枚举映射为 SelectableTag | single | `POST /plans/{id}/days/{day}/completion` |

## 十三、组件区实例与通用组件的组合关系总览

以下表格总结了《组件拆解 V1》中 30+ 组件区实例与本稿 9 个通用组件之间的组合关系。这张表可以直接用作工程师开发组件区时的"积木清单"。

| 页面 | 组件区实例 | 使用的通用组件 |
|---|---|---|
| **首页** | H-1 TopToolBar | TopToolBar |
| | H-2 FocusCard | StatusTagGroup + SummaryCard + ActionButtonGroup |
| | H-3 TodayTaskCard | SplitInfoPanel + ActionButtonGroup |
| | H-4 RecentRecordSummary | SummaryCard |
| | H-5 PendingReturnCard | SummaryCard + ActionButtonGroup |
| | H-6 QuickHelpEntry | SummaryCard + ActionButtonGroup |
| | H-7 BottomTabBar | BottomTabBar |
| **计划页** | P-1 TopToolBar | TopToolBar |
| | P-2 WeekOverviewCard | StatusTagGroup + SummaryCard |
| | P-3 DaySelector | SelectableTagGroup (single) |
| | P-4 DailyTaskPanel | SplitInfoPanel + SummaryCard |
| | P-5 CompletionPanel | SelectableTagGroup (single) + ActionButtonGroup |
| | P-6 WeekExtensionEntry | SummaryCard + ActionButtonGroup |
| | P-7 BottomTabBar | BottomTabBar |
| **记录页** | R-1 TopToolBar | TopToolBar |
| | R-2 QuickCheckPanel | SelectableTagGroup (multiple) + ActionButtonGroup |
| | R-3 EventRecordForm | InputFormSection |
| | R-4 VoiceInputSection | InputFormSection (voice mode) |
| | R-5 RecordTimeline | TimelineList |
| | R-6 BottomTabBar | BottomTabBar |
| **即时求助** | A-1 TopToolBar | TopToolBar |
| | A-2 ScenarioInputPanel | InputFormSection |
| | A-3 ContextCard | StatusTagGroup + SummaryCard |
| | A-4 ThreeStepResultCard | SummaryCard × 3 |
| | A-5 FollowUpActionBar | ActionButtonGroup |
| | A-6 BoundaryNote | SummaryCard (dashed) |
| **消息中心** | M-1 TopToolBar | TopToolBar |
| | M-2 MessageList | TimelineList |
| | M-3 MessageDetail | SummaryCard |
| | M-4 ProcessingStatus | StatusTagGroup |
| **周反馈** | F-1 TopToolBar | TopToolBar |
| | F-2 PositiveChangeCard | SummaryCard (with evidenceText) |
| | F-3 OpportunityCard | SummaryCard |
| | F-4 NextWeekDecisionPanel | SelectableTagGroup (single) + ActionButtonGroup |
| | F-5 ConservativePathNote | SummaryCard (dashed) |

## 十四、组件间的事件流与状态协作模式

虽然每个通用组件的接口是独立的，但在实际组件区中，多个通用组件往往需要协作。以下说明几种最常见的协作模式，帮助工程师理解组件之间如何通过父组件中介完成状态联动。

### 14.1 选中联动模式

**场景：** P-5 CompletionPanel 中，SelectableTagGroup 选中完成状态后，ActionButtonGroup 的按钮应根据选中结果调整文案或可用性。

**协作方式：** 父组件（CompletionPanel 组件区）维护一个页面级状态 `selectedStatus`。SelectableTagGroup 的 `onSelectionChange` 更新该状态；ActionButtonGroup 的 `buttons` 数组根据该状态动态构建。

```typescript
// CompletionPanel 组件区伪代码
function CompletionPanel({ dayTask, onComplete, onNavigateToRecord }) {
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);

  const buttons = useMemo(() => {
    const items: ButtonItem[] = [];
    if (selectedStatus) {
      items.push({ id: 'confirm', text: '确认完成状态', level: 'primary', action: 'confirm' });
    }
    items.push({ id: 'record', text: '完成后去记录', level: 'secondary', action: 'navigate_record' });
    items.push({ id: 'help', text: '现在求助', level: 'tertiary', action: 'navigate_help' });
    return items;
  }, [selectedStatus]);

  return (
    <>
      <SelectableTagGroup
        tags={completionStatusTags}
        mode="single"
        onSelectionChange={(ids) => setSelectedStatus(ids[0] ?? null)}
      />
      <ActionButtonGroup
        buttons={buttons}
        onButtonPress={(action) => {
          if (action === 'confirm') onComplete(selectedStatus);
          if (action === 'navigate_record') onNavigateToRecord();
        }}
      />
    </>
  );
}
```

### 14.2 加载联动模式

**场景：** A-2 ScenarioInputPanel 提交后，A-4 ThreeStepResultCard 需要展示骨架屏等待 AI 结果。

**协作方式：** 页面级状态管理（如即时求助页的 ViewModel）维护 `aiSessionStatus`。InputFormSection 的 `onSubmit` 触发 API 调用并将状态置为 `processing`；ThreeStepResultCard（由 3 个 SummaryCard 组成）在 status == processing 时展示骨架屏，在 status == completed 时渲染 InstantHelpResult 数据。

### 14.3 空态降级模式

**场景：** 首页 H-3 TodayTaskCard 在无活跃计划时不应展示双列面板，而应展示引导文案。

**协作方式：** 父组件（TodayTaskCard 组件区）根据 `today_task` 是否为 null 决定渲染路径。非 null 时渲染 SplitInfoPanel + ActionButtonGroup；null 时渲染 SummaryCard（引导文案）+ ActionButtonGroup（"开始一份计划"按钮）。

## 十五、结论

到这一版为止，9 个通用组件都有了明确的 TypeScript 和 Swift Protocol 双语伪类型签名。每个组件的 Props / Protocol 字段都可以追溯到《数据结构草案 V1》中的具体领域对象字段，回调事件的命名和参数结构遵循统一约定。同时，30+ 组件区实例与 9 个通用组件的组合关系已经在总览表中完全映射。

| 结论项 | 结果 |
|---|---|
| **通用组件数** | 9 个 |
| **双语签名覆盖** | TypeScript + Swift 各 9 套完整签名 |
| **通用类型定义** | 10 个枚举类型 + 8 个基础数据结构 |
| **组件区组合映射** | 30+ 组件区实例全部映射到通用组件积木 |
| **事件协作模式** | 3 种核心模式（选中联动、加载联动、空态降级） |
| **与数据结构草案对齐** | 所有 Props 字段均有对应的领域对象字段来源 |
| **与 AI 输出结构对齐** | InstantHelpResult / PlanGenerationResult / WeeklyFeedbackResult 的消费路径已在映射表中标注 |

| 推荐下一步 | 产出目标 |
|---|---|
| **Prompt 模板 V1** | 基于 AI 输出结构的 schema 和约束编写第一版 Prompt 模板 |
| **端到端联调草案** | 把数据结构 + AI 输出 + 组件接口串成完整联调清单 |
| **组件库代码启动** | 基于本稿签名开始组件库代码实现 |
