"""发展里程碑参考数据。

为 72 条观察项（V1 54 条 + V2.0 新增 18 条）提供：
- milestone_reference: 对应的 CDC/ASQ-3 发展里程碑
- strength_cue: 力量取向观察提示（引导家长发现成功条件）
- sensitive_window: 该能力的发展敏感期说明

来源：
- CDC "Learn the Signs. Act Early." (2024 修订版)
- ASQ-3 (Ages & Stages Questionnaires, Third Edition)
- Mundy & Newell (2007) Joint Attention
- Eisenberg, Spinrad & Eggum (2010) Emotion Regulation
- Tomasello (1995, 2005) Shared Intentionality
- Nelson (1996) Language in Cognitive Development
- Vygotsky (1978) Zone of Proximal Development
- Dunn (1999, 2014) Sensory Processing Framework（V2.0 新增）
- Bowlby (1969/1982) Attachment Theory; Ainsworth (1978) SSP（V2.0 新增）
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# 里程碑参考数据：{item_id: (milestone_reference, strength_cue, sensitive_window)}
# ---------------------------------------------------------------------------

MILESTONE_DATA: dict[str, tuple[str, str, str]] = {
    # =====================================================================
    # 18—24 个月：互动基础建立期
    # =====================================================================

    # A: 共同注意与社交回应
    "18A-01": (
        "CDC 18m: Responds to name；ASQ-3 Communication 18m",
        "记录孩子最容易回应名字的时刻和条件——什么场景、什么语气、什么距离最有效",
        "名字回应在 9-18m 发展，18m 后应较稳定；重点观察稳定性和跨场景性",
    ),
    "18A-02": (
        "CDC 18m: Points to show interest；Mundy & Newell 2007 Joint Attention",
        "记录孩子跟随指向后做了什么——看了多久、是否发出声音、是否靠近",
        "共同注意核心发展窗口 9-18m，18m 后从回应性向主动发起转变",
    ),
    "18A-03": (
        "CDC 18m: Shows you something by holding it out；Tomasello 1995",
        "记录什么东西最容易引发孩子的分享行为——新奇物品、动物、还是声音",
        "主动发起的共同注意（IJA）是 18-24m 的重要发展标志",
    ),

    # B: 表达需求与语言理解
    "18B-01": (
        "CDC 18m: Tries to say words you say；ASQ-3 Communication 18m",
        "记录孩子成功表达需求时用了什么方式——这就是他当前最有效的沟通策略",
        "18-24m 是从前语言沟通向词语表达过渡的关键期",
    ),
    "18B-02": (
        "CDC 18m: Follows one-step directions；ASQ-3 Communication 18m",
        "记录孩子最熟练执行的指令是什么——这些是他已经理解的语言基础",
        "一步指令理解在 12-18m 发展，18m 后应在多场景中出现",
    ),
    "18B-03": (
        "CDC 18m: Points to body parts/familiar objects when asked",
        "记录孩子反应最快的词汇和场景——这些是他的语言理解基础",
        "接受性语言在 12-18m 快速发展，远领先于表达性语言",
    ),

    # C: 模仿、轮流与互动节奏
    "18C-01": (
        "CDC 18m: Copies other children/adults；Meltzoff 1999 Imitation",
        "记录孩子最喜欢模仿的动作——这说明他在主动选择学习内容",
        "动作模仿是 12-18m 的核心学习机制，18-24m 开始延迟模仿",
    ),
    "18C-02": (
        "CDC 18m: Plays simple pretend；Turn-taking as social foundation",
        "记录哪种游戏最容易出现来回轮次——球、积木、还是声音游戏",
        "早期轮流互动为后续对话和社交轮替奠定基础",
    ),
    "18C-03": (
        "CDC 18m: Simple turn-taking emerges；Vygotsky ZPD scaffolding",
        "记录孩子等待时做了什么——看着大人、拍手、还是发出声音催促",
        "等待能力是自我调节的萌芽，18-24m 只需极短等待即可",
    ),

    # D: 情绪过渡与共同调节
    "18D-01": (
        "CDC 18m: Tantrums are common；Eisenberg et al. 2010 Co-regulation",
        "记录孩子最快平静下来时大人做了什么——抱起、转移注意力、还是语言安抚",
        "18-24m 几乎完全依赖照护者外部调节（co-regulation），这是正常的",
    ),
    "18D-02": (
        "CDC 18m: May cling to caregiver in new situations；Attachment theory",
        "记录什么安抚方式最有效——身体接触、声音安抚、还是环境转换",
        "等待耐受力的发展需要反复的安全体验积累",
    ),
    "18D-03": (
        "Eisenberg & Spinrad 2004: External regulation dominates at 18-24m",
        "记录孩子重新回到活动时的过程——是大人带回、还是自己走回来",
        "从崩溃中恢复的能力是情绪调节发展的早期标志",
    ),

    # E: 社交接近与规则适应
    "18E-01": (
        "CDC 18m: Plays beside other children；Parten 1932 Parallel Play",
        "记录孩子最愿意接近的人是谁、在什么情境下——这说明他的社交舒适区在哪",
        "18-24m 以平行游戏为主，面对熟人能接受互动即可",
    ),
    "18E-02": (
        "CDC 18m: Follows simple rules with help；Early rule understanding",
        "记录孩子最容易接受的'先-后'安排是什么——这些是规则理解的起点",
        "简单顺序规则理解在 18-24m 萌芽，完全需要成人支持",
    ),
    "18E-03": (
        "CDC 18m: Helps with simple chores with guidance",
        "记录孩子最愿意配合的日常活动是什么——穿鞋、收玩具、还是擦桌子",
        "配合性行为是社会性发展的早期表现",
    ),

    # F: 游戏、象征与叙事整合
    "18F-01": (
        "CDC 18m: Plays simple pretend（功能性游戏）；Piaget Symbolic Play",
        "记录孩子自发的功能性游戏有哪些——推车、喂娃娃、打电话",
        "功能性游戏是象征性思维的前奏，18-24m 处于从感觉运动向前运算过渡期",
    ),
    "18F-02": (
        "CDC 18m: Simple pretend play emerges；Leslie 1987 Pretend Play",
        "记录孩子模仿了生活中谁的动作——这反映他在理解和重建日常经验",
        "单步假装动作（如喂娃娃）是符号功能萌芽的标志",
    ),
    "18F-03": (
        "Nelson 1996: Event representations emerge at 18-24m",
        "记录孩子是用动作、声音还是手指再次提起刚才的事——这就是早期叙事的种子",
        "对刚发生事件的再现能力在 18-24m 开始萌芽",
    ),

    # =====================================================================
    # 24—36 个月：表达扩展与规则萌芽期
    # =====================================================================

    # A: 共同注意与社交回应
    "24A-01": (
        "CDC 2y: Notices when others are hurt/upset；主动分享注意力成熟化",
        "记录孩子主动分享发现时最常用的方式——说'你看'、拉手、还是指向",
        "24-36m 共同注意从跟随为主转向主动发起为主",
    ),
    "24A-02": (
        "CDC 2y: Says at least two words together；ASQ-3 Communication 24m",
        "记录孩子回应最快的提问类型——是选择题、是非题、还是开放问题",
        "对话性回应是社交沟通成熟的标志",
    ),
    "24A-03": (
        "CDC 2y: Looks at/engages with books；Joint attention in book reading",
        "记录孩子在共读时最长的注意力持续时间和最感兴趣的内容类型",
        "共读中的共同注意是语言学习的重要载体",
    ),

    # B: 表达需求与语言理解
    "24B-01": (
        "CDC 2y: Says at least two words together；ASQ-3 Communication 24m",
        "记录孩子使用双词句/短句的最佳情境——平静时、急切时、还是游戏中",
        "24-30m 是双词句爆发期（词语组合爆炸期）",
    ),
    "24B-02": (
        "CDC 2y: Follows two-step instructions；ASQ-3 Communication 30m",
        "记录孩子最容易完成的两步指令组合——这些是他理解力的锚点",
        "两步指令理解在 24-30m 发展，是认知灵活性的标志",
    ),
    "24B-03": (
        "CDC 2y: Shows more independence；Choice-making as agency expression",
        "记录孩子做选择时的方式——指、说、摇头——每种都是有效表达",
        "选择表达能力是自主性发展的关键窗口",
    ),

    # C: 模仿、轮流与互动节奏
    "24C-01": (
        "CDC 2y: Plays next to/with other children；Turn-taking maturation",
        "记录哪种游戏最容易出现 2-4 轮互动——这就是孩子的互动舒适区",
        "轮流互动在 24-36m 从 1-2 轮提升到 2-4 轮",
    ),
    "24C-02": (
        "CDC 2y: Copies adults and friends；Deferred imitation maturation",
        "记录孩子模仿的两步动作序列——这说明他在理解动作之间的因果关系",
        "两步模仿是序列记忆和因果理解发展的标志",
    ),
    "24C-03": (
        "CDC 2y: Has back-and-forth conversations（2-3 exchanges）",
        "记录孩子在对话中最长能接住几个回合——以及什么话题最能维持",
        "对话轮替在 24-36m 从 1-2 轮提升到 2-3 轮",
    ),

    # D: 情绪过渡与共同调节
    "24D-01": (
        "CDC 2y: Temper tantrums peak；Eisenberg 2010 Co-regulation to self-regulation",
        "记录孩子从不高兴到缓和的过程中，什么提示最有效——预告、选择、还是命名感受",
        "24-36m 是情绪爆发高峰期，同时也是共同调节策略内化的起点",
    ),
    "24D-02": (
        "CDC 2y: Calms down within 10 min after you leave；Emotion naming emerges",
        "记录哪种帮助方式最容易让孩子从僵持转向合作——这就是最有效的共同调节策略",
        "情绪命名和简单选择是 24-36m 最重要的调节支架",
    ),
    "24D-03": (
        "CDC 2y: Shows progress in emotion regulation across situations",
        "记录同一高压场景这周与上周的强度差异——下降了就是进步",
        "固定场景中的情绪强度变化是调节能力发展的可靠指标",
    ),

    # E: 社交接近与规则适应
    "24E-01": (
        "CDC 2y: Plays next to other children；Parten Parallel → Associative Play",
        "记录孩子靠近同龄人时做了什么——观察、模仿、递东西——每种都是社交尝试",
        "24-36m 从平行游戏向联合游戏过渡",
    ),
    "24E-02": (
        "CDC 2y: Follows simple rules；Rule internalization begins",
        "记录孩子最容易遵守的规则是哪些——这些是规则理解的基础",
        "规则内化在 24-36m 开始，仍高度依赖外部提醒",
    ),
    "24E-03": (
        "CDC 2y: Begins to share/take turns with help",
        "记录孩子在帮助下回到规则中时，需要什么类型的支持——提醒、选择、还是等待",
        "分享和轮流的冲突是社会认知发展的必经之路",
    ),

    # F: 游戏、象征与叙事整合
    "24F-01": (
        "CDC 2y: Plays with more than one toy at same time；Multi-step pretend",
        "记录孩子假装游戏中最长的连续步骤数——2步、3步都值得记录",
        "多步假装游戏在 24-36m 发展，反映计划和序列能力",
    ),
    "24F-02": (
        "CDC 2y: Begins to talk about things that happened；Nelson 1996 Narrative",
        "记录孩子主动说起的片段——不论多短，都是叙事能力的种子",
        "过去事件叙述在 24-30m 萌芽，是自传记忆和语言整合的标志",
    ),
    "24F-03": (
        "CDC 2y: Connects words and actions in play；Narrative linking emerges",
        "记录孩子把人物、动作和结果连起来的最长表达——这就是叙事的雏形",
        "语义连接能力在 24-36m 快速发展",
    ),

    # =====================================================================
    # 36—48 个月：叙事整合与社会化准备期
    # =====================================================================

    # A: 共同注意与社交回应
    "36A-01": (
        "CDC 3y: Carries on a conversation（2-3 exchanges）；Initiating & sustaining",
        "记录孩子主动发起分享时的话题——什么最能引发他的表达欲",
        "36-48m 共同注意已内化，重点转向沟通主动性和话题维持",
    ),
    "36A-02": (
        "CDC 3y: Asks who/what/where/why questions；Perspective-taking emerges",
        "记录孩子在交流中调整策略的时刻——换说法、加动作、看反应——这是社交智慧",
        "36-48m 开始关注对方反应并据此调整，是心理理论萌芽的表现",
    ),
    "36A-03": (
        "CDC 3y: Plays with other children；Group attention emerges",
        "记录孩子在集体场景中跟随注意力的时长和方式",
        "集体注意力是入园准备的重要指标",
    ),

    # B: 表达需求与语言理解
    "36B-01": (
        "CDC 3y: Talks well enough for others to understand most of the time",
        "记录孩子用完整句表达的最佳场景——什么情境下他的表达最清晰、最完整",
        "36-48m 是表达从短句向完整句过渡的关键期",
    ),
    "36B-02": (
        "CDC 3y: Follows 2-3 step instructions；Conditional understanding",
        "记录孩子最容易理解的复杂指令类型——带顺序的、带条件的、还是带原因的",
        "条件性理解在 36-48m 发展，是逻辑思维的基础",
    ),
    "36B-03": (
        "CDC 3y: Communication repair attempts；Tomasello 2005",
        "记录孩子修复沟通失败的方式——换说法、加手势、求助——每种都是高级沟通策略",
        "沟通修复能力在 36-48m 开始出现，是语用能力的重要标志",
    ),

    # C: 模仿、轮流与互动节奏
    "36C-01": (
        "CDC 3y: Takes turns in games；Cooperative play emerges",
        "记录孩子在合作活动中最长能维持多少轮——什么类型的活动最能延长互动",
        "36-48m 从联合游戏向合作游戏过渡",
    ),
    "36C-02": (
        "CDC 3y: Imitates complex actions；Deferred imitation is robust",
        "记录孩子延后迁移使用的动作或语言——这是深层学习的证据",
        "延迟模仿和迁移使用在 36-48m 成为重要学习策略",
    ),
    "36C-03": (
        "CDC 3y: Waits for turn with help；Inhibitory control develops",
        "记录孩子等待他人轮次时的策略——看着、数数、自言自语——都是自我调节的方式",
        "抑制控制在 36-48m 快速发展，是执行功能的核心",
    ),

    # D: 情绪过渡与共同调节
    "36D-01": (
        "CDC 3y: Calms down more quickly；Emotion labeling ability emerges",
        "记录孩子第一次在不顺时说出感受的时刻——这是情绪自我调节的里程碑",
        "36-48m 是从共同调节向自我调节过渡的关键期",
    ),
    "36D-02": (
        "CDC 3y: Uses words to describe feelings；Self-regulation strategies emerge",
        "记录孩子最有效的调节方式——深呼吸、暂停、找大人——每种都是他的调节工具箱",
        "简单调节策略的使用在 36-48m 开始内化",
    ),
    "36D-03": (
        "Eisenberg 2010: Recovery speed as regulation indicator",
        "记录恢复速度的变化趋势——比上周快了就是进步",
        "恢复速度是情绪调节能力最可靠的追踪指标",
    ),

    # E: 社交接近与规则适应
    "36E-01": (
        "CDC 3y: Plays with other children；Rule-based game participation",
        "记录孩子理解和参与规则游戏的过程——从旁观到尝试到参与",
        "规则游戏参与在 36-48m 成为重要的社会化指标",
    ),
    "36E-02": (
        "CDC 3y: Takes turns/shares with help；Negotiation attempts emerge",
        "记录孩子尝试协商或接受结果的时刻——每次尝试都是社交能力的进步",
        "协商能力在 36-48m 萌芽，是社交问题解决的基础",
    ),
    "36E-03": (
        "CDC 3y: May get upset with major changes；Adaptation flexibility",
        "记录孩子从观察到加入的过程——先观察多久、什么促使了加入",
        "适应陌生环境的策略（观察→尝试→参与）是社交灵活性的表现",
    ),

    # F: 游戏、象征与叙事整合
    "36F-01": (
        "CDC 3y: Pretend play is more complex；Extended role-play narratives",
        "记录孩子角色扮演中最长的情节线——角色、动作、台词——都是叙事能力",
        "36-48m 是假装游戏从单步到连贯情节的爆发期",
    ),
    "36F-02": (
        "CDC 3y: Tells stories；Narrative structure (beginning-middle-end)",
        "记录孩子按顺序讲述的最长片段——哪怕只有两步也是叙事结构",
        "36-48m 是叙事能力发展的关键窗口，先-然后-最后结构开始出现",
    ),
    "36F-03": (
        "CDC 3y: Connects actions to story；Event integration matures",
        "记录孩子把人物、动作和结果连起来的时刻——这就是整合性叙事的证据",
        "事件整合能力在 36-48m 快速发展，是读写准备的基础",
    ),

    # =====================================================================
    # V2.0 新增：感觉处理与调节（G 组）—— 三阶段共 9 条
    # =====================================================================

    # 18—24 个月
    "18G-01": (
        "Dunn 2014: Sensory threshold and behavioral response patterns emerge 12-24m",
        "记录孩子最能接受的新质地和条件——这说明他目前的舒适范围和扩展方向",
        "18-24m 是感觉偏好稳定化的早期窗口，触觉接受度个体差异极大",
    ),
    "18G-02": (
        "CDC 18m: Developing auditory processing；Dunn 1999 Sensory Profile",
        "记录什么声音环境下孩子最不受影响——这就是他当前的听觉舒适区",
        "18-24m 听觉过滤能力快速发展，日常背景音适应是重要标志",
    ),
    "18G-03": (
        "ASQ-SE2 18m: Tolerates daily care routines；Dunn 2014 Low Registration",
        "记录最容易和最抗拒的照护活动——这帮助找到循序渐进的切入点",
        "日常照护中的触觉接受度在 18-24m 是照护者最关注的感觉议题",
    ),

    # 24—36 个月
    "24G-01": (
        "Dunn 2014: Sensory modulation matures 24-36m；Background noise tolerance",
        "记录孩子在噪音中维持活动的最长时间——这就是他的听觉调节水平",
        "24-36m 是背景噪音中维持注意力的关键发展期",
    ),
    "24G-02": (
        "CDC 2y: Eats a wider variety of food；Dunn 1999 Oral sensory processing",
        "记录孩子最愿意尝试新食物的方式——每种方式都是感觉适应的策略",
        "24-36m 口腔感觉接受度扩展，是饮食多样化的基础",
    ),
    "24G-03": (
        "ASQ-SE2 24m: Engages in messy play with support；Tactile exploration maturation",
        "记录什么帮助让孩子愿意弄脏手——先看大人做、用工具、还是旁边有纸巾",
        "24-36m 触觉探索从回避向主动参与过渡，需要支持性环境",
    ),

    # 36—48 个月
    "36G-01": (
        "Dunn 2014: Sensory self-regulation in group settings matures 36-48m",
        "记录孩子在集体环境中的调节方式——走到安静角落、捂耳朵、找大人——都是策略",
        "36-48m 集体环境中的感觉调节能力是入园适应的重要指标",
    ),
    "36G-02": (
        "CDC 3y: Uses words to describe feelings；Sensory vocabulary emerges",
        "记录孩子第一次用语言表达感觉偏好的时刻——这是自我调节的飞跃",
        "36-48m 开始能用语言而非行为表达感觉不适，是重要的调节里程碑",
    ),
    "36G-03": (
        "ASQ-SE2 36m: Cooperates with daily care despite discomfort；Dunn 2014",
        "记录什么预告方式最有效——说步骤、给选择、用计时器——每种都是预期管理策略",
        "36-48m 在预告和选择支持下的配合能力是感觉调节成熟的标志",
    ),

    # =====================================================================
    # V2.0 新增：依恋安全与基地行为（H 组）—— 三阶段共 9 条
    # =====================================================================

    # 18—24 个月
    "18H-01": (
        "Ainsworth 1978: Secure base behavior；Bowlby 1969 Attachment phases III-IV",
        "记录孩子探索前靠近大人的方式——看一眼、碰一下、拉衣角——每种都是安全确认",
        "18-24m 是安全基地行为（explore → check back → explore）建立的核心期",
    ),
    "18H-02": (
        "CDC 18m: Clings to adults in new situations；Ainsworth 1978 SSP reunion behavior",
        "记录孩子在重聚时如何靠近——跑过来、接受拥抱——这是安全依恋的标志行为",
        "18-24m 分离-重聚反应模式是依恋安全性的最佳观察窗口",
    ),
    "18H-03": (
        "Bowlby 1982: Attachment as safe haven；CDC 18m: Seeks comfort from caregiver",
        "记录什么情况下孩子会寻找大人——这说明他已将照护者建立为安全港湾",
        "寻求安慰行为在 12-18m 建立，18-24m 应跨情境出现",
    ),

    # 24—36 个月
    "24H-01": (
        "Ainsworth 1978: Secure base exploration range expands 24-36m",
        "记录孩子探索的距离和回看的频率——距离增大且回看减少说明安全感在增强",
        "24-36m 安全基地的探索半径显著扩大，是独立性发展的基础",
    ),
    "24H-02": (
        "Bowlby 1982: Separation protest normative at 24-30m；Ainsworth SSP",
        "记录什么告别方式最有效——仪式感、简短、说好接的时间——找到最适合的方式",
        "24-36m 分离适应能力快速发展，是入托准备的核心议题",
    ),
    "24H-03": (
        "CDC 2y: Shows affection to familiar people；Reunion behavior as attachment indicator",
        "记录重聚时孩子的表现——跑过来、说发生的事、微笑——每种都是安全依恋的表达",
        "积极的重聚反应是安全依恋的最可靠指标之一",
    ),

    # 36—48 个月
    "36H-01": (
        "Bowlby 1982: Goal-corrected partnership emerges 36-48m；Separation tolerance",
        "记录孩子在分离后多久能安定投入——这就是他当前的分离适应水平",
        "36-48m 分离耐受力增强，开始理解'大人会回来'的时间概念",
    ),
    "36H-02": (
        "Ainsworth 1978: Seeking comfort after distress；Safe haven function",
        "记录孩子寻求安慰的方式——跑过来说、事后才讲——每种都是信任的表达",
        "36-48m 寻求安慰的方式从行为为主转向语言为主",
    ),
    "36H-03": (
        "CDC 3y: Separates easily from parents；Bowlby Goal-corrected partnership",
        "记录孩子在等待时的策略——叫名字、拍手、等待、自己玩——每种都是调节策略",
        "36-48m 开始发展在照护者注意力不可得时的自我调节能力",
    ),
}
"""72 条观察项的里程碑参考数据（V1 54 条 + V2.0 新增 18 条）。

格式：{item_id: (milestone_reference, strength_cue, sensitive_window)}
"""


def enrich_item_milestone(item_id: str) -> tuple[str, str, str]:
    """获取指定观察项的里程碑参考数据。

    Returns:
        (milestone_reference, strength_cue, sensitive_window) 三元组。
        如果 item_id 未找到，返回空字符串三元组。
    """
    return MILESTONE_DATA.get(item_id, ("", "", ""))
