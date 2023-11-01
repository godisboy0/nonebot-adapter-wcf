import sys
import asyncio
from nonebot.adapters.console import Adapter as ConsoleAdapter
from nonebot.adapters import Adapter as BaseAdapter

from typing import Any, Dict, List, Callable, Optional, Awaitable

from textual.color import Color
from nonebot.drivers import Driver
from nonebot.typing import overrides
from nonechat import Frontend, ConsoleSetting
from nonebot.adapters.console.config import Config
from nonebot.adapters.console.backend import AdapterConsoleBackend
from nonebot.adapters.console.event import Event

from adapters.wechatferry.bot import Bot as WechatFerryBot
from adapters.wechatferry.event import (
    PrivateMessageEvent as WcfPrivateMsgEvent, 
    GroupMessageEvent as WcfGroupMsgEvent,
    Sender
)
from adapters.wechatferry.message import MessageSegment as WcfMessageSeg, Message as WcfMessage

BOT_ID = "wechatferry_console"

"""
一个简单的想法，把从bot中接收到的onebot格式的消息转换成console格式的消息
这样可以方便地在控制台中测试bot的功能
"""


class OneBotV11ConsoleAdapter(BaseAdapter):
    @overrides(BaseAdapter)
    def __init__(self, driver: Driver, **kwargs: Any) -> None:
        super().__init__(driver, **kwargs)
        self.console_config = Config.parse_obj(self.config)
        self.bot = WechatFerryBot(self, BOT_ID)

        self._task: Optional[asyncio.Task] = None
        self._frontend: Optional[Frontend[AdapterConsoleBackend]] = None
        self._stdout = sys.stdout
        self.clients: List[Callable[[WechatFerryBot,
                                     str, Dict[str, Any]], Awaitable[Any]]] = []
        self.group_mode = False

        self.setup()

    @staticmethod
    @overrides(BaseAdapter)
    def get_name() -> str:
        return "Console"

    def setup(self):
        if not self.console_config.console_headless_mode:
            self.driver.on_startup(self._start)
            self.driver.on_shutdown(self._shutdown)

    async def _start(self) -> None:
        self._frontend = Frontend(
            AdapterConsoleBackend,
            ConsoleSetting(
                title="Nonebot",
                sub_title="welcome to Console",
                toolbar_exit="❌",
                toolbar_back="⬅",
                icon_color=Color.parse("#EA5252"),
            ),
        )
        self._frontend.backend.set_adapter(self)
        self._task = asyncio.create_task(self._frontend.run_async())
        self.bot_connect(self.bot)

    async def _shutdown(self) -> None:
        self.bot_disconnect(self.bot)
        if self._frontend:
            self._frontend.exit()
        if self._task:
            await self._task

    def post_event(self, event: Event) -> None:
        msg = event.get_message()
        text = msg.extract_plain_text()
        if text.strip() == "_gc_":
            # 模拟群组消息。
            self.group_mode = True
            self._call_api(self.bot, "send_msg",
                           message="群组模式。输入uid$msg发送消息。_qgc_退出")
            return
        elif text.strip() == "_qgc_":
            self.group_mode = False
            self._call_api(self.bot, "send_msg", message="退出群组模式。")

        if self.group_mode:
            # 此时格式应该为 uid$msg
            uid, msg = text.split('$')
        else:
            uid = event.get_user_id()
            msg = text

        args = {}
        args['message'] = WcfMessage(
            WcfMessageSeg.text(msg.extract_plain_text()))
        args['original_message'] = args["message"]
        args.update({
            "post_type": "message",
            "time": event.time,
            "wx_type": 1,
            "self_id": event.self_id,
            "user_id": uid,
            "message_id": "test_msg_id",
            "raw_message": msg.xml,
            "font": 12,     # meaningless for wechat, but required by onebot 11
            "sender": Sender(user_id=uid),
            "to_me": True,
        })
        if self.group_mode:
            args.update({
                "message_type": "group",
                "sub_type": "normal",
                "group_id": msg.roomid,
                "at_list": []
            })
            new_event = WcfPrivateMsgEvent(**args)
        else:
            args.update({
                "message_type": "private",
                "sub_type": "friend",
            })
            new_event = WcfGroupMsgEvent(**args)
        asyncio.create_task(self.bot.handle_event(new_event))

    @overrides(BaseAdapter)
    async def _call_api(self, bot: WechatFerryBot, api: str, **data: Any) -> None:
        await self._frontend.call(api, data)
