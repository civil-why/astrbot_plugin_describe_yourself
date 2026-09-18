import json
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


class MyPlugin(Star):
    KV_KEY = "custom_keyword_replies"

    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("自我介绍 + 关键词回复插件已初始化")

    # ================= 工具方法 =================
    async def _load_keywords(self) -> dict:
        """从 KV 存储加载关键词-回复映射。"""
        raw = await self.get_kv_data(self.KV_KEY, "{}")
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    async def _save_keywords(self, mapping: dict):
        await self.put_kv_data(self.KV_KEY, json.dumps(mapping, ensure_ascii=False))

    def _get_intro_message(self) -> str:
        cfg = self.context.get_config()
        return cfg.get("intro_message", "大家好！我是astrbot，请多多指教～")

    # ================= 功能一：指令触发自我介绍 =================
    @filter.command("自我介绍")
    async def introduce(self, event: AstrMessageEvent):
        """用户发送 /自我介绍 时，回复预设的自我介绍文本。"""
        user_name = event.get_sender_name()
        yield event.plain_result(f"你好, {user_name}! {self._get_intro_message()}")

    # ================= 功能二：Bot 入群自动发送 =================
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_increase(self, event: AstrMessageEvent):
        """监听群聊事件，当 Bot 自己被拉入群时自动发送自我介绍。"""
        raw = event.message_obj.raw_message
        if not (hasattr(raw, "notice_type") and raw.notice_type == "group_increase"):
            return
        if str(event.message_obj.self_id) != str(raw.user_id):
            return  # 不是 Bot 自己进群
        logger.info(f"Bot 被拉入新群 {raw.group_id}，发送自我介绍")
        yield event.plain_result(self._get_intro_message())

    # ================= 功能三：关键词直接回复（绕过 LLM） =================
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_keyword(self, event: AstrMessageEvent):
        """匹配自定义关键词，直接回复预设文本，不经过 LLM。"""
        msg = event.message_str.strip()
        # 跳过空消息和以 / 开头的指令
        if not msg or msg.startswith("/"):
            return

        keywords = await self._load_keywords()
        if not keywords:
            return

        mode = self.context.get_config().get("keyword_match_mode", "contains")

        for kw, reply in keywords.items():
            hit = (kw == msg) if mode == "exact" else (kw in msg)
            if hit:
                logger.info(f"命中关键词 [{kw}]，直接回复")
                yield event.plain_result(reply)
                event.stop_event()  # 关键：阻止事件继续传给 LLM
                return

    # ================= 功能四：关键词管理指令 =================
    @filter.command("添加关键词")
    async def add_keyword(self, event: AstrMessageEvent):
        """用法: /添加关键词 关键词 | 回复内容"""
        parts = event.message_str.split(maxsplit=1)
        if len(parts) < 2 or "|" not in parts[1]:
            yield event.plain_result("用法: /添加关键词 关键词 | 回复内容")
            return
        kw, reply = parts[1].split("|", 1)
        kw, reply = kw.strip(), reply.strip()
        if not kw or not reply:
            yield event.plain_result("关键词和回复内容都不能为空")
            return

        keywords = await self._load_keywords()
        action = "更新" if kw in keywords else "添加"
        keywords[kw] = reply
        await self._save_keywords(keywords)
        yield event.plain_result(f"已{action}关键词: {kw}")

    @filter.command("删除关键词")
    async def del_keyword(self, event: AstrMessageEvent):
        """用法: /删除关键词 关键词"""
        parts = event.message_str.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: /删除关键词 关键词")
            return
        kw = parts[1].strip()

        keywords = await self._load_keywords()
        if kw in keywords:
            del keywords[kw]
            await self._save_keywords(keywords)
            yield event.plain_result(f"已删除关键词: {kw}")
        else:
            yield event.plain_result(f"未找到关键词: {kw}")

    @filter.command("列出关键词")
    async def list_keyword(self, event: AstrMessageEvent):
        """用法: /列出关键词"""
        keywords = await self._load_keywords()
        if not keywords:
            yield event.plain_result("当前没有自定义关键词。")
            return
        lines = ["当前关键词列表:"]
        for i, (kw, reply) in enumerate(keywords.items(), 1):
            lines.append(f"{i}. {kw} → {reply}")
        yield event.plain_result("\n".join(lines))

    async def terminate(self):
        logger.info("自我介绍 + 关键词回复插件已卸载")