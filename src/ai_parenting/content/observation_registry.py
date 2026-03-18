"""观察项注册表。

将《三阶段具体观察项清单 V1》中的 54 条基础观察项 + V2.0 新增 18 条观察项，
合计 72 条结构化观察项，可供系统按阶段、主题、焦点查询，
驱动轻量打点、微计划生成和趋势判断。

V2.0 新增:
- 感觉处理与调节（G 组）：每阶段 3 条，聚焦日常可观察的感觉反应行为
  不使用"感统失调""感觉寻求"等学科术语，以家长能直接观察的行为描述
- 依恋安全与基地行为（H 组）：每阶段 3 条，聚焦分离-重聚、安全基地循环
  不使用"依恋障碍""不安全依恋"等诊断标签，以安全感的日常表现描述
- milestone_reference、strength_cue、sensitive_window 字段自动注入

V2.1 力量取向记录框架重构:
- 全部 72 条 record_metric 统一为力量取向正向描述
- 消除"是否出现""是否…""需不需…"等缺陷导向二元判断
- 统一为"什么条件/场景下最容易出现""什么方式最有效"等正向描述模式
- 引导家长记录"成功条件"而非"缺陷清单"

设计文档来源：docs/ai_parenting_observation_checklist_v1.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ai_parenting.models.enums import (
    ChildStage,
    DevTheme,
    InterventionFocus,
)
from ai_parenting.content.milestone_references import enrich_item_milestone


# ---------------------------------------------------------------------------
# 观察项数据结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObservationItem:
    """单条观察项。

    Attributes:
        item_id: 唯一标识（格式：{阶段前缀}{主题字母}-{序号}，如 18A-01）
        stage: 所属年龄阶段
        theme: 所属发展主题
        description: 可直接打点的观察项描述
        record_metric: 建议记录口径（力量取向：优先记录"出现时的条件"）
        intervention_focus: 对应干预焦点
        record_type: 更适合的记录单元类型
        priority: 本阶段内的优先级（high=首页优先展示，medium=活跃项，low=后台观察）
        milestone_reference: 对应的发展里程碑参考（CDC/ASQ 来源）
        strength_cue: 力量取向观察提示——引导家长发现成功条件
        sensitive_window: 该能力的发展敏感期描述（帮助理解为什么在此阶段观察）
    """

    item_id: str
    stage: ChildStage
    theme: DevTheme
    description: str
    record_metric: str
    intervention_focus: InterventionFocus
    record_type: Literal["checkpoint", "event", "review"] = "checkpoint"
    priority: Literal["high", "medium", "low"] = "medium"
    milestone_reference: str = ""
    strength_cue: str = ""
    sensitive_window: str = ""


# ---------------------------------------------------------------------------
# 18—24 个月观察项（互动基础建立期）
# ---------------------------------------------------------------------------

_ITEMS_18_24: list[ObservationItem] = [
    # 共同注意与社交回应
    ObservationItem(
        item_id="18A-01", stage=ChildStage.M18_24, theme=DevTheme.JOINT_ATTENTION,
        description="被叫名字时，大多数时候会转头、看向说话人或停下当前动作",
        record_metric="出现时的场景和条件（什么语气、距离、活动状态下回应最快）",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
        priority="high",
    ),
    ObservationItem(
        item_id="18A-02", stage=ChildStage.M18_24, theme=DevTheme.JOINT_ATTENTION,
        description="大人指向一个东西时，会顺着看过去或靠近看",
        record_metric="跟随后的反应（看了多久、靠近了吗、有无发声）；哪类场景最容易出现",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
        priority="high",
    ),
    ObservationItem(
        item_id="18A-03", stage=ChildStage.M18_24, theme=DevTheme.JOINT_ATTENTION,
        description="看到喜欢或新鲜的东西时，会看物再看人，像是在'分享发现'",
        record_metric="触发物和场景；伴随的表达方式（发声、指向、拉手）",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
    ),
    # 表达需求与语言理解
    ObservationItem(
        item_id="18B-01", stage=ChildStage.M18_24, theme=DevTheme.EXPRESSION_NEED,
        description="想要某样东西时，会用指向、伸手、眼神、声音或词语表达，而不只是哭闹",
        record_metric="使用了哪种表达方式（手势/眼神/声音/词语）；什么情境下最容易有效表达",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
        priority="high",
    ),
    ObservationItem(
        item_id="18B-02", stage=ChildStage.M18_24, theme=DevTheme.EXPRESSION_NEED,
        description="听到熟悉的一步指令后，常能做出相应动作，例如'把球给我''过来'",
        record_metric="能执行的指令内容和场景；哪些指令最熟练、反应最快",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
    ),
    ObservationItem(
        item_id="18B-03", stage=ChildStage.M18_24, theme=DevTheme.EXPRESSION_NEED,
        description="在熟悉生活场景中，会对常见物品或动作词有反应",
        record_metric="反应最快的词汇和场景；出现反应时的具体表现（看向、靠近、执行）",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
    ),
    # 模仿、轮流与互动节奏
    ObservationItem(
        item_id="18C-01", stage=ChildStage.M18_24, theme=DevTheme.IMITATION_TURN,
        description="愿意模仿简单动作，例如拍手、挥手、敲敲桌子",
        record_metric="最喜欢模仿的动作；即时模仿还是稍后再现；什么条件下最愿意模仿",
        intervention_focus=InterventionFocus.ACTION_IMITATE,
        priority="high",
    ),
    ObservationItem(
        item_id="18C-02", stage=ChildStage.M18_24, theme=DevTheme.IMITATION_TURN,
        description="能接住 1—2 个来回轮次，例如递玩具、推球回来",
        record_metric="能维持的轮次数；什么游戏最容易达到多轮；孩子主动发起还是跟随",
        intervention_focus=InterventionFocus.TURN_SCAFFOLD,
    ),
    ObservationItem(
        item_id="18C-03", stage=ChildStage.M18_24, theme=DevTheme.IMITATION_TURN,
        description="在互动游戏中，能短暂等待大人做完再轮到自己",
        record_metric="等待时的表现（看着大人、拍手、发声）；什么游戏下最容易等待",
        intervention_focus=InterventionFocus.TURN_SCAFFOLD,
    ),
    # 情绪过渡与共同调节
    ObservationItem(
        item_id="18D-01", stage=ChildStage.M18_24, theme=DevTheme.EMOTION_TRANSITION,
        description="从喜欢的活动转到另一件事时，会出现不高兴，但在成人帮助下能逐渐缓和",
        record_metric="大人用了什么方式帮助缓和（预告/转移/安抚）；最快平静时的条件",
        intervention_focus=InterventionFocus.TRANSITION_PREP,
        record_type="event",
        priority="high",
    ),
    ObservationItem(
        item_id="18D-02", stage=ChildStage.M18_24, theme=DevTheme.EMOTION_TRANSITION,
        description="等待片刻或暂时拿不到东西时，不舒服的反应是否能被安抚下来",
        record_metric="最有效的安抚方式（身体接触/声音/转移注意力）；安抚后的转变过程",
        intervention_focus=InterventionFocus.EMOTION_NAMING,
        record_type="event",
    ),
    ObservationItem(
        item_id="18D-03", stage=ChildStage.M18_24, theme=DevTheme.EMOTION_TRANSITION,
        description="哭闹或卡住时，能否在熟悉照护者陪伴下重新回到活动中",
        record_metric="什么方式能帮助重新回到活动（大人带回/自己走回来）；回到原活动还是转移到新活动",
        intervention_focus=InterventionFocus.EMOTION_NAMING,
        record_type="event",
    ),
    # 社交接近与规则适应
    ObservationItem(
        item_id="18E-01", stage=ChildStage.M18_24, theme=DevTheme.SOCIAL_APPROACH,
        description="面对熟悉亲友时，会靠近、观察或接受互动，而不是始终完全回避",
        record_metric="最愿意接近的人和情境；靠近后的互动方式（观察/微笑/递东西）",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    ObservationItem(
        item_id="18E-02", stage=ChildStage.M18_24, theme=DevTheme.SOCIAL_APPROACH,
        description="能在成人支持下接受非常简单的'先—后'安排",
        record_metric="最容易接受的'先-后'安排内容；什么类型的支持最有效",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    ObservationItem(
        item_id="18E-03", stage=ChildStage.M18_24, theme=DevTheme.SOCIAL_APPROACH,
        description="在短时间等待或收拾时，是否能接受成人带着一起完成",
        record_metric="最愿意配合的日常活动（穿鞋/收玩具/擦桌子）；配合时的参与方式",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    # 游戏、象征与叙事整合
    ObservationItem(
        item_id="18F-01", stage=ChildStage.M18_24, theme=DevTheme.PLAY_NARRATIVE,
        description="会按物品功能去玩，例如推车、喂娃娃、拿勺子喂玩偶",
        record_metric="自发出现的功能性游戏有哪些；是自发发起还是跟做",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
        priority="low",
    ),
    ObservationItem(
        item_id="18F-02", stage=ChildStage.M18_24, theme=DevTheme.PLAY_NARRATIVE,
        description="在大人带动下，会出现单步假装动作，例如给玩具'吃饭''睡觉'",
        record_metric="假装了什么内容；是跟做还是自发延伸；模仿了生活中谁的动作",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
        priority="low",
    ),
    ObservationItem(
        item_id="18F-03", stage=ChildStage.M18_24, theme=DevTheme.PLAY_NARRATIVE,
        description="对刚刚发生的小事，会通过动作、指向或声音再次提起",
        record_metric="用什么方式再次提起（动作/声音/指向）；提起时的表达方式和分享意图",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
        priority="low",
    ),
    # V2.0 新增：感觉处理与调节（G 组）
    ObservationItem(
        item_id="18G-01", stage=ChildStage.M18_24, theme=DevTheme.SENSORY_PROCESSING,
        description="接触新质地的食物或材料时，会看一看、试一试，而不是立刻躲开或大哭",
        record_metric="孩子最能接受的新质地是什么；什么条件下愿意尝试（大人先示范/放在桌上自己拿）",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        priority="medium",
    ),
    ObservationItem(
        item_id="18G-02", stage=ChildStage.M18_24, theme=DevTheme.SENSORY_PROCESSING,
        description="在日常噪音环境中（商场、家人聊天、洗衣机声），能维持正在做的事",
        record_metric="什么声音环境下最不受影响；出现干扰时的表现（捂耳朵/找大人/哭闹/继续玩）",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        record_type="event",
        priority="medium",
    ),
    ObservationItem(
        item_id="18G-03", stage=ChildStage.M18_24, theme=DevTheme.SENSORY_PROCESSING,
        description="愿意接受日常身体接触，例如穿衣、洗脸、擦手，虽可能不喜欢但不持续激烈抗拒",
        record_metric="最容易接受的和最抗拒的日常照护是哪些；什么方式能帮助缓和（预告/选择/慢慢来）",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        record_type="event",
        priority="medium",
    ),
    # V2.0 新增：依恋安全与基地行为（H 组）
    ObservationItem(
        item_id="18H-01", stage=ChildStage.M18_24, theme=DevTheme.ATTACHMENT_SECURITY,
        description="在新环境中，会先靠近照护者、观察一下，再慢慢探索周围",
        record_metric="探索前靠近大人的方式（看一眼/碰一下/拉衣角）；开始探索的等待时间",
        intervention_focus=InterventionFocus.SECURE_BASE,
        priority="high",
    ),
    ObservationItem(
        item_id="18H-02", stage=ChildStage.M18_24, theme=DevTheme.ATTACHMENT_SECURITY,
        description="短暂分离后（去另一个房间、上厕所），重聚时会主动靠近或接受安抚",
        record_metric="什么类型的分离反应最轻（去哪里/多久/谁带走）；重聚时最常见的表现（主动靠近/接受拥抱）",
        intervention_focus=InterventionFocus.SECURE_BASE,
        record_type="event",
        priority="high",
    ),
    ObservationItem(
        item_id="18H-03", stage=ChildStage.M18_24, theme=DevTheme.ATTACHMENT_SECURITY,
        description="受到惊吓或不舒服时，会寻找熟悉的照护者或向照护者靠近",
        record_metric="什么情况下会寻找大人（摔倒/陌生人/突然的声音）；找到大人后多久能安定",
        intervention_focus=InterventionFocus.SECURE_BASE,
        record_type="event",
        priority="high",
    ),
]

# ---------------------------------------------------------------------------
# 24—36 个月观察项（表达扩展与规则萌芽期）
# ---------------------------------------------------------------------------

_ITEMS_24_36: list[ObservationItem] = [
    # 共同注意与社交回应
    ObservationItem(
        item_id="24A-01", stage=ChildStage.M24_36, theme=DevTheme.JOINT_ATTENTION,
        description="会主动把自己看到的东西指给大人看，或主动说'你看'",
        record_metric="什么场景下最容易自发分享（户外/看到新事物/吃饭时）；大人回应后孩子的反应",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
    ),
    ObservationItem(
        item_id="24A-02", stage=ChildStage.M24_36, theme=DevTheme.JOINT_ATTENTION,
        description="听到大人简单问候或提问时，会用眼神、动作或词语接回应答",
        record_metric="什么话题和场景下回应最积极；用了哪种方式回应（看/点头/说词语）",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
    ),
    ObservationItem(
        item_id="24A-03", stage=ChildStage.M24_36, theme=DevTheme.JOINT_ATTENTION,
        description="在共读或看图时，能跟着大人一起关注同一画面并短暂停留",
        record_metric="什么类型的图画或话题最能吸引持续关注；共同注意持续最久时的条件",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
    ),
    # 表达需求与语言理解
    ObservationItem(
        item_id="24B-01", stage=ChildStage.M24_36, theme=DevTheme.EXPRESSION_NEED,
        description="想要东西、拒绝或求助时，开始使用双词句或短句",
        record_metric="哪些需求场景下最常用句子表达；使用的词句有哪些（举例记录）",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
        priority="high",
    ),
    ObservationItem(
        item_id="24B-02", stage=ChildStage.M24_36, theme=DevTheme.EXPRESSION_NEED,
        description="能理解两步简短指令，例如'去拿杯子，再放桌上'",
        record_metric="什么类型的两步指令完成得最顺畅；完成时的表情和反应",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
        priority="high",
    ),
    ObservationItem(
        item_id="24B-03", stage=ChildStage.M24_36, theme=DevTheme.EXPRESSION_NEED,
        description="当大人给出两个选择时，能用动作或语言表达自己的选择",
        record_metric="什么类型的选择最容易做出回应（食物/玩具/活动）；用了哪种方式表达选择",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
        priority="high",
    ),
    # 模仿、轮流与互动节奏
    ObservationItem(
        item_id="24C-01", stage=ChildStage.M24_36, theme=DevTheme.IMITATION_TURN,
        description="能在游戏中轮流 2—4 个回合，而不是很快离开或只抢回合",
        record_metric="什么游戏下轮次最多；孩子主动等待对方时的表现（看着/催促/数数）",
        intervention_focus=InterventionFocus.TURN_SCAFFOLD,
        priority="high",
    ),
    ObservationItem(
        item_id="24C-02", stage=ChildStage.M24_36, theme=DevTheme.IMITATION_TURN,
        description="会模仿两步相关动作，例如'拿杯子—喂娃娃'或'敲门—开门'",
        record_metric="最喜欢模仿的动作组合有哪些；什么场景下模仿最活跃",
        intervention_focus=InterventionFocus.ACTION_IMITATE,
    ),
    ObservationItem(
        item_id="24C-03", stage=ChildStage.M24_36, theme=DevTheme.IMITATION_TURN,
        description="在简短对话里，能接住一问一答或来回两三句的互动",
        record_metric="什么话题下对话最流畅；最长能来回几句；孩子最喜欢聊的内容",
        intervention_focus=InterventionFocus.TURN_SCAFFOLD,
    ),
    # 情绪过渡与共同调节
    ObservationItem(
        item_id="24D-01", stage=ChildStage.M24_36, theme=DevTheme.EMOTION_TRANSITION,
        description="被拒绝、等待或停止喜欢活动时，会明显不高兴，但在提示下有机会慢慢缓和",
        record_metric="什么提示方式最有效（预告/选择/共情）；缓和得最快时的条件",
        intervention_focus=InterventionFocus.TRANSITION_PREP,
        record_type="event",
        priority="high",
    ),
    ObservationItem(
        item_id="24D-02", stage=ChildStage.M24_36, theme=DevTheme.EMOTION_TRANSITION,
        description="当大人帮助命名感受或给出简单选择时，孩子有时能从僵持转向合作",
        record_metric="哪种提示最容易促成合作（命名感受/给选择/转移注意力）；合作时孩子的表现",
        intervention_focus=InterventionFocus.EMOTION_NAMING,
        record_type="event",
    ),
    ObservationItem(
        item_id="24D-03", stage=ChildStage.M24_36, theme=DevTheme.EMOTION_TRANSITION,
        description="在固定高压场景（穿衣、洗澡、收玩具），反应强度是否开始下降",
        record_metric="哪个高压场景进步最明显；进步时大人做了什么不同的事",
        intervention_focus=InterventionFocus.TRANSITION_PREP,
        record_type="review",
    ),
    # 社交接近与规则适应
    ObservationItem(
        item_id="24E-01", stage=ChildStage.M24_36, theme=DevTheme.SOCIAL_APPROACH,
        description="遇到同龄孩子时，会靠近、观察、平行玩，或短暂参与同一活动",
        record_metric="和谁在一起时最容易接近同伴；接近后的互动方式（观察/平行玩/递东西）",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    ObservationItem(
        item_id="24E-02", stage=ChildStage.M24_36, theme=DevTheme.SOCIAL_APPROACH,
        description="在成人提醒下，能接受简单规则，例如排队、轮流、收玩具",
        record_metric="哪种规则最容易接受；什么类型的提醒最有效（口头/手势/示范）",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    ObservationItem(
        item_id="24E-03", stage=ChildStage.M24_36, theme=DevTheme.SOCIAL_APPROACH,
        description="对分享、等待轮次或被打断时，虽会抗拒，但开始能在帮助下重新回到规则中",
        record_metric="什么帮助方式最容易让孩子重新回到规则（给选择/用计时器/先轮到他）",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    # 游戏、象征与叙事整合
    ObservationItem(
        item_id="24F-01", stage=ChildStage.M24_36, theme=DevTheme.PLAY_NARRATIVE,
        description="会进行连续两三步的假装游戏，例如做饭、喂饭、收拾餐具",
        record_metric="最喜欢的假装主题有哪些；情节最丰富时的条件（和谁玩/用什么道具）",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
    ),
    ObservationItem(
        item_id="24F-02", stage=ChildStage.M24_36, theme=DevTheme.PLAY_NARRATIVE,
        description="能说出刚刚发生的小片段，例如'去公园了''爸爸开车'",
        record_metric="什么类型的事件最容易引发自发讲述；讲述时使用了哪些词汇和表达",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
    ),
    ObservationItem(
        item_id="24F-03", stage=ChildStage.M24_36, theme=DevTheme.PLAY_NARRATIVE,
        description="看图、玩玩具或经历一件小事后，能把人、物和动作连起来表达",
        record_metric="什么活动之后最容易出现连接表达；连接方式（用'和''然后'还是动作串联）",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
    ),
    # V2.0 新增：感觉处理与调节（G 组）
    ObservationItem(
        item_id="24G-01", stage=ChildStage.M24_36, theme=DevTheme.SENSORY_PROCESSING,
        description="能在较吵闹的环境中（其他小朋友在玩、电视开着）维持自己的活动一小会儿",
        record_metric="在什么噪音水平下能维持多久；被干扰后用什么方式回到活动中",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        priority="medium",
    ),
    ObservationItem(
        item_id="24G-02", stage=ChildStage.M24_36, theme=DevTheme.SENSORY_PROCESSING,
        description="对新食物的质地、温度有反应，但愿意在鼓励下尝试一小口或摸一摸",
        record_metric="最愿意尝试的方式（闻/摸/舔/咬一口）；什么条件最容易接受新体验",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        priority="medium",
    ),
    ObservationItem(
        item_id="24G-03", stage=ChildStage.M24_36, theme=DevTheme.SENSORY_PROCESSING,
        description="在需要弄脏手的活动中（画画、玩沙、揉面团），虽可能犹豫但能逐步参与",
        record_metric="最能接受的'弄脏'活动是什么；需要什么帮助才愿意参与（先看大人做/用工具代替/旁边有纸巾）",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        record_type="event",
        priority="medium",
    ),
    # V2.0 新增：依恋安全与基地行为（H 组）
    ObservationItem(
        item_id="24H-01", stage=ChildStage.M24_36, theme=DevTheme.ATTACHMENT_SECURITY,
        description="在游乐场或亲友家时，会离开大人去探索，但隔一会儿会回来看看或说点什么",
        record_metric="离开探索的距离和时间；回来看大人时的方式（看一眼/跑回来/叫一声）",
        intervention_focus=InterventionFocus.SECURE_BASE,
        priority="high",
    ),
    ObservationItem(
        item_id="24H-02", stage=ChildStage.M24_36, theme=DevTheme.ATTACHMENT_SECURITY,
        description="在幼儿园或陌生场景的分离时刻，虽会不舍但能在成人安抚下逐渐安定",
        record_metric="分离时的反应强度和持续时间；什么告别方式最有效（仪式感/简短/说好接的时间）",
        intervention_focus=InterventionFocus.SECURE_BASE,
        record_type="event",
        priority="high",
    ),
    ObservationItem(
        item_id="24H-03", stage=ChildStage.M24_36, theme=DevTheme.ATTACHMENT_SECURITY,
        description="重聚时（接放学、起床后见到大人），会表达高兴或主动靠近分享经历",
        record_metric="重聚时的典型表现（跑过来/微笑/说发生了什么）；过渡到下一个活动的方式",
        intervention_focus=InterventionFocus.SECURE_BASE,
        record_type="event",
        priority="high",
    ),
]

# ---------------------------------------------------------------------------
# 36—48 个月观察项（叙事整合与社会化准备期）
# ---------------------------------------------------------------------------

_ITEMS_36_48: list[ObservationItem] = [
    # 共同注意与社交回应
    ObservationItem(
        item_id="36A-01", stage=ChildStage.M36_48, theme=DevTheme.JOINT_ATTENTION,
        description="会主动告诉大人自己看到、想到或经历的事，并期待对方回应",
        record_metric="什么时候最爱主动分享（回家路上/睡前/看到新东西时）；分享时的表达方式",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
    ),
    ObservationItem(
        item_id="36A-02", stage=ChildStage.M36_48, theme=DevTheme.JOINT_ATTENTION,
        description="在交流中，会看对方反应并据此继续、停顿或换一种说法",
        record_metric="和谁交流时社交节奏感最好；什么话题下最能做到察看对方反应",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
    ),
    ObservationItem(
        item_id="36A-03", stage=ChildStage.M36_48, theme=DevTheme.JOINT_ATTENTION,
        description="在集体或多人场景中，能跟随当前共同关注点短暂参与",
        record_metric="什么类型的集体活动最容易参与（唱歌/手工/故事）；参与时的表现",
        intervention_focus=InterventionFocus.WAIT_RESPOND,
    ),
    # 表达需求与语言理解
    ObservationItem(
        item_id="36B-01", stage=ChildStage.M36_48, theme=DevTheme.EXPRESSION_NEED,
        description="会用更完整的句子表达请求、拒绝、解释或协商",
        record_metric="什么场景下句子最完整（日常请求/解释理由/协商规则）；令人惊喜的表达举例",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
        priority="high",
    ),
    ObservationItem(
        item_id="36B-02", stage=ChildStage.M36_48, theme=DevTheme.EXPRESSION_NEED,
        description="能理解带顺序、条件或原因的简短说明，并按顺序完成",
        record_metric="哪类条件句最能理解（因为…所以/先…再/如果…就）；完成得最顺的场景",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
    ),
    ObservationItem(
        item_id="36B-03", stage=ChildStage.M36_48, theme=DevTheme.EXPRESSION_NEED,
        description="当别人没听懂时，有时会换一种说法、补充动作或补充信息",
        record_metric="什么情况下最可能尝试换说法；用了什么替代方式（加动作/换词/指东西）",
        intervention_focus=InterventionFocus.CHOICE_EXPRESS,
    ),
    # 模仿、轮流与互动节奏
    ObservationItem(
        item_id="36C-01", stage=ChildStage.M36_48, theme=DevTheme.IMITATION_TURN,
        description="在合作活动中，能维持多轮互动，例如一起搭建、轮流讲、轮流做",
        record_metric="什么合作活动轮次最多（搭积木/轮流画/传球）；最多能维持几轮",
        intervention_focus=InterventionFocus.TURN_SCAFFOLD,
        priority="high",
    ),
    ObservationItem(
        item_id="36C-02", stage=ChildStage.M36_48, theme=DevTheme.IMITATION_TURN,
        description="会模仿较完整的动作或语言形式，并在稍后自己再次使用",
        record_metric="最喜欢模仿的内容（大人说话/动画片/生活场景）；延后再现时的创意变化",
        intervention_focus=InterventionFocus.ACTION_IMITATE,
    ),
    ObservationItem(
        item_id="36C-03", stage=ChildStage.M36_48, theme=DevTheme.IMITATION_TURN,
        description="在对话或游戏中，能等待他人轮次，不总是打断或立刻抢回主导",
        record_metric="什么活动下等待最从容；等待时的自我调节方式（观察/自言自语/数数）",
        intervention_focus=InterventionFocus.TURN_SCAFFOLD,
    ),
    # 情绪过渡与共同调节
    ObservationItem(
        item_id="36D-01", stage=ChildStage.M36_48, theme=DevTheme.EMOTION_TRANSITION,
        description="遇到不顺、等待或被拒绝时，开始能说出自己的感受、想法或不满",
        record_metric="什么场景下最能用语言表达感受；使用了哪些情绪词汇（生气/难过/不想）",
        intervention_focus=InterventionFocus.EMOTION_NAMING,
        record_type="event",
        priority="high",
    ),
    ObservationItem(
        item_id="36D-02", stage=ChildStage.M36_48, theme=DevTheme.EMOTION_TRANSITION,
        description="在提醒下，会使用简单调节方式，例如深呼吸、暂停、找大人帮忙",
        record_metric="哪种调节方式孩子最愿意用；什么场景下调节效果最好",
        intervention_focus=InterventionFocus.EMOTION_NAMING,
        record_type="event",
    ),
    ObservationItem(
        item_id="36D-03", stage=ChildStage.M36_48, theme=DevTheme.EMOTION_TRANSITION,
        description="高压场景后的恢复速度是否较前更快，且能重新回到原任务",
        record_metric="恢复最快时的条件（谁陪着/什么场景/用了什么方式）；回到任务后的状态",
        intervention_focus=InterventionFocus.TRANSITION_PREP,
        record_type="review",
    ),
    # 社交接近与规则适应
    ObservationItem(
        item_id="36E-01", stage=ChildStage.M36_48, theme=DevTheme.SOCIAL_APPROACH,
        description="在同伴互动中，能理解并参与简单规则游戏",
        record_metric="什么规则游戏参与得最投入（躲猫猫/老鹰捉小鸡/轮流）；和谁玩时最顺利",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
        priority="high",
    ),
    ObservationItem(
        item_id="36E-02", stage=ChildStage.M36_48, theme=DevTheme.SOCIAL_APPROACH,
        description="发生玩具冲突、排队或等待时，开始能在帮助下协商、轮流或接受后果",
        record_metric="什么方式帮助协商最有效（大人引导/用语言模板/设定时间）；成功协商的情境",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    ObservationItem(
        item_id="36E-03", stage=ChildStage.M36_48, theme=DevTheme.SOCIAL_APPROACH,
        description="在陌生或半熟悉场景中，虽可能先观察，但能逐步进入活动",
        record_metric="什么类型的活动最容易从观察转为参与；从观察到加入的过程和时间",
        intervention_focus=InterventionFocus.SOCIAL_REHEARSE,
    ),
    # 游戏、象征与叙事整合
    ObservationItem(
        item_id="36F-01", stage=ChildStage.M36_48, theme=DevTheme.PLAY_NARRATIVE,
        description="会开展较连贯的角色扮演或假装情节，而不只是单步动作重复",
        record_metric="最喜欢的角色扮演主题（做饭/看病/上课）；情节最丰富时的条件",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
        priority="high",
    ),
    ObservationItem(
        item_id="36F-02", stage=ChildStage.M36_48, theme=DevTheme.PLAY_NARRATIVE,
        description="能按'先—然后—最后'或相近顺序讲述一件刚发生的小事",
        record_metric="什么类型的事件讲得最有顺序（自己经历的/看到的/游戏中的）；使用了哪些顺序词",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
        priority="high",
    ),
    ObservationItem(
        item_id="36F-03", stage=ChildStage.M36_48, theme=DevTheme.PLAY_NARRATIVE,
        description="在讲述、看图或游戏后，能把人物、动作、结果简单连起来",
        record_metric="什么情境下连接表达最流畅（讲故事/看图说话/游戏复述）；最长的连接叙述举例",
        intervention_focus=InterventionFocus.NARRATIVE_SCAFFOLD,
    ),
    # V2.0 新增：感觉处理与调节（G 组）
    ObservationItem(
        item_id="36G-01", stage=ChildStage.M36_48, theme=DevTheme.SENSORY_PROCESSING,
        description="在集体活动环境中（多人同时说话、音乐、跑动），能跟随当前活动而不持续躲避",
        record_metric="什么类型的集体环境最能适应；不适应时的表现和自我调节方式",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        priority="medium",
    ),
    ObservationItem(
        item_id="36G-02", stage=ChildStage.M36_48, theme=DevTheme.SENSORY_PROCESSING,
        description="对不喜欢的感觉体验，开始能用语言表达'不要''不喜欢'，而不只是躲或哭",
        record_metric="能表达不喜欢的体验有哪些；是在平静时还是当下能说出来",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        record_type="event",
        priority="medium",
    ),
    ObservationItem(
        item_id="36G-03", stage=ChildStage.M36_48, theme=DevTheme.SENSORY_PROCESSING,
        description="在日常照护（洗头、剪指甲、穿特定衣物）中，虽不喜欢但能在预告和选择下配合完成",
        record_metric="哪些照护活动最需要准备；什么预告方式最有效（说步骤/给选择/用计时器）",
        intervention_focus=InterventionFocus.SENSORY_MODULATE,
        record_type="event",
        priority="medium",
    ),
    # V2.0 新增：依恋安全与基地行为（H 组）
    ObservationItem(
        item_id="36H-01", stage=ChildStage.M36_48, theme=DevTheme.ATTACHMENT_SECURITY,
        description="能接受在幼儿园或活动课上和照护者分开一段时间，期间能参与活动",
        record_metric="分离后多久能安定投入活动；什么过渡方式最有效（带一个小物件/特定告别仪式/老师引导）",
        intervention_focus=InterventionFocus.SECURE_BASE,
        priority="high",
    ),
    ObservationItem(
        item_id="36H-02", stage=ChildStage.M36_48, theme=DevTheme.ATTACHMENT_SECURITY,
        description="遇到困难或受委屈后，愿意告诉照护者并接受安慰，之后能继续活动",
        record_metric="寻求安慰的方式（跑过来说/哭着找/事后才讲）；安慰后能否恢复",
        intervention_focus=InterventionFocus.SECURE_BASE,
        record_type="event",
        priority="high",
    ),
    ObservationItem(
        item_id="36H-03", stage=ChildStage.M36_48, theme=DevTheme.ATTACHMENT_SECURITY,
        description="在照护者注意力暂时不在自己身上时（打电话、照顾弟妹），能短暂自己玩或等待",
        record_metric="能自己维持多久；用什么方式引起注意（叫名字/拍手/等待/发脾气）",
        intervention_focus=InterventionFocus.SECURE_BASE,
        record_type="event",
        priority="medium",
    ),
]


# ---------------------------------------------------------------------------
# 注册表：全部 72 条观察项（注入里程碑参考数据）
# ---------------------------------------------------------------------------


def _build_enriched_items() -> tuple[ObservationItem, ...]:
    """构建带里程碑参考数据的观察项元组。

    对于每条观察项，如果其 milestone_reference 为空，
    则从 milestone_references.py 中查找并创建新实例注入。
    """
    raw_items = _ITEMS_18_24 + _ITEMS_24_36 + _ITEMS_36_48
    enriched = []
    for item in raw_items:
        if not item.milestone_reference:
            ref, cue, window = enrich_item_milestone(item.item_id)
            if ref:
                # frozen dataclass 无法直接修改，需要创建新实例
                import dataclasses
                item = dataclasses.replace(
                    item,
                    milestone_reference=ref,
                    strength_cue=cue,
                    sensitive_window=window,
                )
        enriched.append(item)
    return tuple(enriched)


ALL_ITEMS: tuple[ObservationItem, ...] = _build_enriched_items()

# 索引：按 item_id 快速查找
_BY_ID: dict[str, ObservationItem] = {item.item_id: item for item in ALL_ITEMS}


# ---------------------------------------------------------------------------
# 查询 API
# ---------------------------------------------------------------------------


def get_item(item_id: str) -> ObservationItem | None:
    """按 ID 查找单条观察项。"""
    return _BY_ID.get(item_id)


def get_items_by_stage(stage: ChildStage) -> list[ObservationItem]:
    """返回指定阶段的全部观察项。"""
    return [item for item in ALL_ITEMS if item.stage == stage]


def get_items_by_theme(theme: DevTheme, stage: ChildStage | None = None) -> list[ObservationItem]:
    """返回指定主题（可选阶段过滤）的观察项。"""
    items = [item for item in ALL_ITEMS if item.theme == theme]
    if stage is not None:
        items = [item for item in items if item.stage == stage]
    return items


def get_items_by_focus(focus: InterventionFocus, stage: ChildStage | None = None) -> list[ObservationItem]:
    """返回指定干预焦点（可选阶段过滤）的观察项。"""
    items = [item for item in ALL_ITEMS if item.intervention_focus == focus]
    if stage is not None:
        items = [item for item in items if item.stage == stage]
    return items


def get_active_items(stage: ChildStage, max_count: int = 18) -> list[ObservationItem]:
    """返回指定阶段的活跃观察项（按优先级排序）。

    遵循设计文档建议：18-24m 约 12 条，24-36m 约 15 条，36-48m 约 15-18 条。
    """
    priority_order = {"high": 0, "medium": 1, "low": 2}
    items = get_items_by_stage(stage)
    items.sort(key=lambda x: priority_order.get(x.priority, 1))
    return items[:max_count]


def get_daily_items(stage: ChildStage, theme: DevTheme | None = None, count: int = 4) -> list[ObservationItem]:
    """返回每日建议呈现的观察项（优先 high 级别）。

    18-24m 建议 3-4 条，24-36m 建议 4-5 条，36-48m 建议 4-5 条。
    """
    items = get_items_by_stage(stage)
    if theme is not None:
        # 优先当前主题
        theme_items = [i for i in items if i.theme == theme and i.priority == "high"]
        other_high = [i for i in items if i.theme != theme and i.priority == "high"]
        items = theme_items + other_high
    else:
        items = [i for i in items if i.priority == "high"]
    return items[:count]


# ---------------------------------------------------------------------------
# 阶段优先主题建议
# ---------------------------------------------------------------------------


STAGE_PRIORITY_THEMES: dict[ChildStage, list[DevTheme]] = {
    ChildStage.M18_24: [
        DevTheme.JOINT_ATTENTION,
        DevTheme.EXPRESSION_NEED,
        DevTheme.IMITATION_TURN,
        DevTheme.EMOTION_TRANSITION,
        DevTheme.ATTACHMENT_SECURITY,   # V2.0：依恋安全在 18-24m 是核心观察维度
    ],
    ChildStage.M24_36: [
        DevTheme.EXPRESSION_NEED,
        DevTheme.IMITATION_TURN,
        DevTheme.EMOTION_TRANSITION,
        DevTheme.SOCIAL_APPROACH,
        DevTheme.ATTACHMENT_SECURITY,   # V2.0：分离-重聚适应期
    ],
    ChildStage.M36_48: [
        DevTheme.PLAY_NARRATIVE,
        DevTheme.SOCIAL_APPROACH,
        DevTheme.EMOTION_TRANSITION,
        DevTheme.IMITATION_TURN,
        DevTheme.SENSORY_PROCESSING,    # V2.0：入园准备需关注感觉适应
    ],
}
"""每个阶段首页优先展示的发展主题。
来源：观测模型 V1.1 第四章 + V2.0 感觉处理与依恋安全补充。
"""
