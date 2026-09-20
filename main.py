from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("自我介绍 + 关键词回复插件已初始化")

    # ================= 工具方法 =================
    def _get_intro_message(self) -> str:
        """从配置读取自我介绍文本。"""
        cfg = self.context.get_config()
        msg = cfg.get("intro_message", "")
        if not msg:
            logger.warning("配置项 intro_message 为空，请到后台插件配置中填写自我介绍内容")
            return "（自我介绍未配置，请到 AstrBot 后台插件配置中设置）"
        return msg

    def _get_keyword_replies(self) -> dict:
        cfg = self.context.get_config()
        data = cfg.get("keyword_replies", {})
        if not isinstance(data, dict):
            logger.warning("配置项 keyword_replies 格式异常，已忽略")
            return {}
        return data

    # ================= 功能一：指令触发自我介绍 =================
    @filter.command("自我介绍")
    async def introduce(self, event: AstrMessageEvent):
        user_name = event.get_sender_name()
        yield event.plain_result(f"你好, {user_name}! {self._get_intro_message()}")

    # ================= 功能二：Bot 入群自动发送 =================
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_increase(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        if not (hasattr(raw, "notice_type") and raw.notice_type == "group_increase"):
            return
        if str(event.message_obj.self_id) != str(raw.user_id):
            return
        logger.info(f"Bot 被拉入新群 {raw.group_id}，发送自我介绍")
        yield event.plain_result(self._get_intro_message())

    # ================= 功能三：关键词直接回复 =================
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_keyword(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        if not msg or msg.startswith("/"):
            return

        keywords = self._get_keyword_replies()
        if not keywords:
            return

        mode = self.context.get_config().get("keyword_match_mode", "contains")

        for kw, reply in keywords.items():
            hit = (kw == msg) if mode == "exact" else (kw in msg)
            if hit:
                logger.info(f"命中关键词 [{kw}]，直接回复")
                yield event.plain_result(str(reply))
                event.stop_event()
                return

    # ================= 功能四：只读查询指令 =================
    @filter.command("列出关键词")
    async def list_keyword(self, event: AstrMessageEvent):
        keywords = self._get_keyword_replies()
        if not keywords:
            yield event.plain_result("当前没有配置关键词，请在 AstrBot 后台插件配置中添加。")
            return
        lines = ["当前关键词列表:"]
        for i, (kw, reply) in enumerate(keywords.items(), 1):
            lines.append(f"{i}. {kw} → {reply}")
        lines.append("\n如需修改，请到 AstrBot 后台插件配置页面编辑。")
        yield event.plain_result("\n".join(lines))

    async def terminate(self):
        logger.info("自我介绍 + 关键词回复插件已卸载")