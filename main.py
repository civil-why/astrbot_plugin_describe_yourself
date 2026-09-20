from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("自我介绍插件已初始化")

    def _get_intro_message(self) -> str:
        """从配置读取自我介绍文本。"""
        cfg = self.context.get_config()
        logger.info(f"cfg 类型: {type(cfg)}")
        logger.info(f"cfg 内容: {cfg}")
        logger.info(f"intro_message 值: {repr(cfg.get('intro_message'))}")
        msg = cfg.get("intro_message", "")
        if not msg:
            logger.warning("配置项 intro_message 为空，请到后台插件配置中填写")
            return "（自我介绍未配置，请到 AstrBot 后台插件配置中设置）"
        return msg

    # ===== 功能一：指令触发自我介绍 =====
    @filter.command("自我介绍")
    async def introduce(self, event: AstrMessageEvent):
        user_name = event.get_sender_name()
        yield event.plain_result(f"你好, {user_name}! {self._get_intro_message()}")

    # ===== 功能二：Bot 自己进群时自动发送 =====
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_increase(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        if not (hasattr(raw, "notice_type") and raw.notice_type == "group_increase"):
            return
        if str(event.message_obj.self_id) != str(raw.user_id):
            return
        logger.info(f"Bot 被拉入新群 {raw.group_id}，发送自我介绍")
        yield event.plain_result(self._get_intro_message())

    async def terminate(self):
        logger.info("自我介绍插件已卸载")