import sys
import asyncio
from nonebot.adapters import Adapter as BaseAdapter

from typing import Any, Dict, List, Callable, Optional, Awaitable

from textual.color import Color
from nonebot.drivers import Driver
from nonebot.typing import overrides
from nonechat import Frontend, ConsoleSetting
from nonebot.adapters.console.config import Config
from nonebot.adapters.console.backend import AdapterConsoleBackend
from nonebot.adapters.console.event import Event, MessageEvent
from nonechat.message import Text, ConsoleMessage

from adapters.wechatferry.bot import Bot as WechatFerryBot
from adapters.wechatferry.event import (
    PrivateMessageEvent as WcfPrivateMsgEvent,
    GroupMessageEvent as WcfGroupMsgEvent,
    Sender
)
from adapters.wechatferry.message import MessageSegment as WcfMessageSeg, Message as WcfMessage
from adapters.wechatferry.basemodel import UserInfo as WcfUserInfo
from typing import Literal
from adapters.wechatferry.utils import logger

BOT_ID = "wechatferry_console"

"""
一个简单的想法，把从bot中接收到的onebot格式的消息转换成console格式的消息
这样可以方便地在控制台中测试bot的功能
onebot11标准要求：https://github.com/botuniverse/onebot-11/blob/master/README.md
onebot11 message segment 类型: https://github.com/botuniverse/onebot-11/blob/master/message/segment.md
"""


class SimpleMsg:

    def __init__(self, msg_id: int, msg_type: Literal["text", "image", "voice", "refer", "video", "file", "link"], 
                 raw_msg: str, msg: str, speaker_id, room_id=None):
        self.msg_id = msg_id
        self.msg_type = msg_type
        self.raw_msg = raw_msg
        self.msg = msg
        self.room_id = room_id
        self.speaker_id = speaker_id


speaker_uid = "User"
msg_id_seq = 0
msg_store: dict[int, SimpleMsg] = {}


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
        self.always_at = False
        self.show_msg_id = False

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
                title="onebot11-adapter-console",
                sub_title="welcome using for test",
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
        # 功能越来越多，改成更清晰的流水账写法吧= =
        if not isinstance(event, MessageEvent):
            asyncio.create_task(self._call_api(
                self.bot, "send_text", text="暂不支持非消息事件"))
            return

        global speaker_uid, msg_id_seq, msg_store
        msg = event.get_message()
        text: str = msg.extract_plain_text().strip()
        if text.startswith(":set"):
            # 这是设置模式，用于各种调参。
            if text == ":set":
                # 这里显示帮助文档
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=":set [key] [value]"))
                return
            elif text == ":set grp":
                # 模拟群组消息。
                self.group_mode = True
                asyncio.create_task(self._call_api(self.bot, "send_text",
                                                   text=f"群组模式。当前用户 {speaker_uid}。\n:set qgrp退出群组，\n:set uid xx 使用新用户身份", to_wxid=event.get_user_id()))
                return
            elif text == ":set qgrp":
                self.group_mode = False
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text="退出群组模式。", to_wxid=event.get_user_id()))
                return
            elif text.startswith(":set uid "):
                uid = text.split(":set uid ")[1].strip()
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"以{uid}发言", to_wxid=event.get_user_id()))
                speaker_uid = uid
                return
            elif text.startswith(":set tome true"):
                # 从此就一直at机器人，
                self.always_at = True
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"总是at机器人，有时候会造成测试问题，需要时打开", to_wxid=event.get_user_id()))
                return
            elif text.startswith(":set tome false"):
                # 从此在群聊中需要显式at机器人
                self.always_at = False
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"不再总是at机器人，在群聊中@bot才会被机器人处理，在测试中很有用", to_wxid=event.get_user_id()))
                return
            elif text.startswith(":set showid true"):
                # 显示消息id
                self.show_msg_id = True
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"开始显示消息id", to_wxid=event.get_user_id()))
                return
            elif text.startswith(":set showid false"):
                # 不显示消息id
                self.show_msg_id = False
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"不再显示消息id", to_wxid=event.get_user_id()))
                return
            elif text.startswith(":set"):
                # 这里是设置各种参数
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text="暂不支持的设置"))
                return
        # 接下来是对消息的各种特殊处理，主要支持不同的消息格式。

        at_users = []
        msg_id_seq += 1
        if self.show_msg_id:
            asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"发出的消息id: {msg_id_seq}", to_wxid=event.get_user_id()))
        final_msg_args = {}
        if '@' in text:
            # @符号以后的都认为是另一个用户名
            at_users = [x for x in text.split('@')[1:] if x]
            text = text.split('@')[0].strip()


        if text.startswith("image:"):
            # 发送一个图片消息过去。
            file_path = text.split("image:")[1].strip()
            msg_store[msg_id_seq] = SimpleMsg(
                msg_id_seq, "image", text, file_path, speaker_uid, None if not self.group_mode else "console_group")
            final_msg_args['message'] = WcfMessage(
                WcfMessageSeg.image(file_path))
        elif text.startswith("voice:"):
            # 发送一个音频消息过去。
            file_path = text.split("voice:")[1].strip()
            msg_store[msg_id_seq] = SimpleMsg(
                msg_id_seq, "voice", text, file_path, speaker_uid, None if not self.group_mode else "console_group")
            final_msg_args['message'] = WcfMessage(
                WcfMessageSeg.record(file_path))
        elif text.startswith("video:"):
            # 发送一个视频消息过去。
            file_path = text.split("video:")[1].strip()
            msg_store[msg_id_seq] = SimpleMsg(
                msg_id_seq, "video", text, file_path, speaker_uid, None if not self.group_mode else "console_group")
            final_msg_args['message'] = WcfMessage(
                WcfMessageSeg.video(file_path))
        elif text.startswith("file:"):
            # 发送一个文件消息过去。
            file_path = text.split("file:")[1].strip()
            msg_store[msg_id_seq] = SimpleMsg(
                msg_id_seq, "file", text, file_path, speaker_uid, None if not self.group_mode else "console_group")
            final_msg_args['message'] = WcfMessage(
                WcfMessageSeg('file', {'file': file_path}))
        elif text.startswith("link:"):
            splited_text = text.split("link:")[1].strip()
            splited_text = splited_text.split("#")
            if len(splited_text) != 4:
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text="链接消息格式应当为>> link:title#desc#url#img_path", to_wxid=event.get_user_id()))
                return
            title, desc, url, img_path = splited_text
            link_msg = WcfMessage(
                WcfMessageSeg.share(title, desc, url, img_path))
            final_msg_args['message'] = link_msg
            msg_store[msg_id_seq] = SimpleMsg(
                msg_id_seq, "link", text, link_msg[0].data, speaker_uid, None if not self.group_mode else "console_group")
        elif text.startswith("refer:"):
            # 发送一个引用消息过去，refer后面的就是id
            refer_content = text.split("refer:")[1].strip()
            splited_refer_content = refer_content.split(" ")
            if len(splited_refer_content) < 2:
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text="引用消息格式应当为>> refer:refered_msg_id textmsg。\n输入:set showid true可以显示消息的msg_id", to_wxid=event.get_user_id()))
                return
            refer_msg = splited_refer_content[0]
            refer_text_msg = " ".join(splited_refer_content[1:])
            msg_store[msg_id_seq] = SimpleMsg(
                msg_id_seq, "refer", text, refer_msg, speaker_uid, None if not self.group_mode else "console_group")
            if not refer_msg.isdigit() or int(refer_msg) not in msg_store:
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"引用消息{refer_msg}不存在", to_wxid=event.get_user_id()))
                return
            referd_msg = extract_refer_msg(msg_store[int(refer_msg)], refer_text_msg)
            if refer_msg is None:
                asyncio.create_task(self._call_api(
                    self.bot, "send_text", text=f"引用消息{refer_msg}解析失败，可能是被引用消息的类型未支持", to_wxid=event.get_user_id()))
                return
            final_msg_args['message'] = referd_msg
        else:
            # 发送一个文本消息过去。
            msg_store[msg_id_seq] = SimpleMsg(msg_id_seq, "text", text, text, speaker_uid, None if not self.group_mode else "console_group")
            final_msg_args['message'] = WcfMessage(
                WcfMessageSeg.text(text))
            
        if at_users:
            final_msg_args['message'] = final_msg_args['message'] + [WcfMessageSeg.at(
                user_id) for user_id in at_users]
        final_msg_args['original_message'] = final_msg_args["message"]
        final_msg_args.update({
            "post_type": "message",
            "time": event.time.timestamp(),
            "self_id": event.self_id,
            "user_id": speaker_uid,
            "message_id": msg_id_seq,
            "raw_message": text,
            "font": 12,     # meaningless for wechat, but required by onebot 11
            "sender": Sender(user_id=speaker_uid),
            "to_me": not self.group_mode or 'bot' in at_users or self.always_at,
        })

        if self.group_mode:
            final_msg_args.update({
                "message_type": "group",
                "sub_type": "normal",
                "group_id": "console_group"
            })
            new_event = WcfGroupMsgEvent(**final_msg_args)
        else:
            final_msg_args.update({
                "message_type": "private",
                "sub_type": "friend",
            })
            new_event = WcfPrivateMsgEvent(**final_msg_args)

        asyncio.create_task(self.bot.handle_event(new_event))

    @overrides(BaseAdapter)
    async def _call_api(self, bot: WechatFerryBot, api: str, **data: Any) -> Any:
        # 目前的api只有3种：send_text, send_image, send_music。统一给改了
        global msg_id_seq
        msg_id_seq += 1
        if self.show_msg_id:
            msg_id_seq_str = f"{msg_id_seq}. "
        else:
            msg_id_seq_str = ""
        if api == "send_text":
            text = data['text']
            new_data = {"user_id": data['to_wxid'],
                        "message": ConsoleMessage([Text(f'{msg_id_seq_str}{text}')])}
        elif api == "send_image":
            file_path = data['file']
            new_data = {"user_id": data['to_wxid'], "message": ConsoleMessage(
                [Text(f"{msg_id_seq_str}[图片] {file_path}")])}
        elif api == "send_music":
            file_path = data['audio']
            new_data = {"user_id": data['to_wxid'], "message": ConsoleMessage(
                [Text(f"{msg_id_seq_str}[音乐] {file_path}")])}
        elif api == "get_user_info":
            user_id = data['user_id']
            return WcfUserInfo(wx_id=user_id, code=user_id, wx_name=user_id, gender="😝")
        elif api == "get_alias_in_chatroom":
            return data['user_id']
        else:
            logger.warning(f"不支持的api: {api}")
            return

        await self._frontend.call("send_msg", new_data)

def extract_refer_msg(refer_msg: SimpleMsg, refer_text_msg: str) -> Optional[WcfMessage]:
    types = ["text", "image", "voice", "video"]
    for t in types:
        if refer_msg.msg_type == t:
            return WcfMessage(WcfMessageSeg('wx_refer', {
                'content': refer_text_msg,
                'refer': {
                    'id': refer_msg.msg_id,
                    'type': t,
                    'speaker_id': refer_msg.speaker_id,
                    'content': refer_msg.msg
                }
            }))
    return None