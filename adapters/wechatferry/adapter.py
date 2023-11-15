from typing import Any, Optional
from typing_extensions import override
from nonebot import get_driver
from nonebot.drivers import (
    Driver
)
import asyncio
from concurrent.futures import ThreadPoolExecutor

from nonebot.adapters import Adapter as BaseAdapter
from queue import Empty
from nonebot.utils import escape_tag

from .bot import Bot
from .event import Event, GroupMessageEvent
from .config import AdapterConfig
from wcferry import Wcf, WxMsg
from .eventconverter import convert_to_event
from .exception import WcfInitFailedException
from .utils import logger
from .api import API
from .sqldb import database

adapter_config = AdapterConfig.parse_obj(get_driver().config)

DB = database(adapter_config.db_path)
if not DB.table_exists("msg"):
    DB.create_table(
        'create table msg ( \
            id integer primary key autoincrement, \
            room_id text, \
            user_id text, \
            msg_text text, \
            msg_type text, \
            at_users text, \
            msg_id text, \
            raw_msg text, \
            msg_time text \
        )'
    )

if not DB.table_exists("raw_msg"):
    DB.create_table(
        'create table raw_msg ( \
            id integer primary key autoincrement, \
            msg_id text, \
            msg_type text, \
            msg_time text, \
            msg_sign text, \
            msg_xml text, \
            msg_sender text, \
            msg_roomid text, \
            msg_content text, \
            msg_thumb text, \
            msg_extra text \
        )'
    )


rsv_executor = ThreadPoolExecutor(max_workers=1)


class Adapter(BaseAdapter):

    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.driver.on_startup(self._setup)
        self.driver.on_shutdown(self._shutdown)

    async def _shutdown(self) -> None:
        self.bot_disconnect(self.bot)
        if self.wcf:
            self.wcf.disable_recv_msg()
            self.wcf.cleanup()
        if self.receive_message_task:
            self.receive_message_task.cancel()

    async def _setup(self) -> None:
        try:
            self.wcf = Wcf(debug=adapter_config.debug)
            self.login_bot_id = self.wcf.get_user_info()['wxid']
            self.bot = Bot(adapter=self, self_id=self.login_bot_id)
            self.wcf.enable_receiving_msg()
            self.api = API(self.wcf)
            self.receive_message_task = asyncio.create_task(
                self._receive_message())
            self.bot_connect(self.bot)
            logger.info("wcf initialized successful, ready to go!")
        except Exception as e:
            logger.error("Failed to initialize Wcf: ", e)
            raise WcfInitFailedException() from e

    async def _receive_message(self) -> None:
        while self.wcf.is_receiving_msg():
            try:
                msg: WxMsg = await asyncio.get_event_loop().run_in_executor(rsv_executor, self.wcf.get_msg)
                logger.debug(
                    f"Received message from wcf: {escape_tag(str(msg))}")
                event = self.wcf_msg_to_event(msg)
                if event:
                    await record_msg(event)
                    asyncio.create_task(self.bot.handle_event(event))
                else:
                    await record_raw_msg(msg)
            except Empty:
                continue  # Empty message
            except Exception as e:
                logger.error("Receiving message error:", e)

    def wcf_msg_to_event(self, msg: WxMsg) -> Optional[Event]:
        """将wcf消息转换为Event"""
        if not msg:
            return None
        return convert_to_event(msg, self.login_bot_id, self.wcf)

    @classmethod
    @override
    def get_name(cls) -> str:
        return "wechatferry"

    @override
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        """调用API"""
        logger.debug(
            f"Calling API {escape_tag(api)} with data: {escape_tag(str(data))}")
        try:
            await self.api.call_api(api, data)
        except Exception as e:
            logger.error(f"Calling API {escape_tag(api)} failed: {e}")
            self.record_failed_api(api, data)
            raise e

    def record_failed_api(self, api, data):
        import json
        with open("error.txt", "a") as f:
            d = {
                "api": api,
                "data_str": str(data),
            }
            try:
                json.dumps(data, ensure_ascii=False, indent=2)
                d["data_json"] = data
            except:
                pass
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


async def record_msg(event: Event):
    try:
        room_id = str(event.group_id) if isinstance(
            event, GroupMessageEvent) else None
        user_id = str(event.user_id)
        msg_text = event.message.extract_plain_text()
        msg_type = ",".join([seg.type for seg in event.message])
        at_users = ",".join([seg.data["qq"]
                            for seg in event.message if seg.type == "at"])
        msg_id = event.message_id
        msg_time = event.time
        raw_msg = str(event.raw_message)

        DB.insert(
            'insert into msg (room_id, user_id, msg_text, msg_type, at_users, msg_id, raw_msg, msg_time) values (?, ?, ?, ?, ?, ?, ?, ?)',
            room_id, user_id, msg_text, msg_type, at_users, msg_id, raw_msg, msg_time
        )
    except Exception as e:
        logger.error("Record message error:", e)


async def record_raw_msg(msg: WxMsg):
    try:
        msg_id = msg.id
        msg_type = msg.type
        msg_time = msg.ts
        msg_sign = msg.sign
        msg_xml = msg.xml
        msg_sender = msg.sender
        msg_roomid = msg.roomid
        msg_content = msg.content
        msg_thumb = msg.thumb
        msg_extra = msg.extra

        DB.insert(
            'insert into raw_msg (msg_id, msg_type, msg_time, msg_sign, msg_xml, msg_sender, msg_roomid, msg_content, msg_thumb, msg_extra) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            msg_id, msg_type, msg_time, msg_sign, msg_xml, msg_sender, msg_roomid, msg_content, msg_thumb, msg_extra
        )
    except Exception as e:
        logger.error("Record raw message error:", e)