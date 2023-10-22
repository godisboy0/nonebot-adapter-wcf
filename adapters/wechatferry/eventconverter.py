from wcferry import Wcf, WxMsg
from .event import Event
from .message import MessageSegment, Message
from .type import WxType
from .utils import logger
from . import event
import inspect
from typing import TypeVar, Type
import re
from nonebot.utils import escape_tag


E = TypeVar("E", bound=Event)


known_event_type: dict[str, Type[E]] = {}

for model_name in dir(event):
    model = getattr(event, model_name)
    if not inspect.isclass(model) or not issubclass(model, Event):
        continue
    wx_raw_type = model.__fields__.get("wx_raw_type")
    if wx_raw_type is None:
        logger.warning(
            f"Event model {escape_tag(model_name)} has no wx_raw_type field.")
        continue
    wx_raw_type = wx_raw_type.default
    known_event_type[wx_raw_type] = model


def __get_mention_list(req: WxMsg) -> list[str]:
    if req.xml is not None:
        pattern = r'<atuserlist>(.*?)</atuserlist>'
        match = re.search(pattern, req.xml)
        if match:
            atuserlist = match.group(1)
            return [user_id for user_id in atuserlist.split(',')]
    return []


def convert_to_event(msg: WxMsg, login_wx_id: str, wcf: Wcf = None) -> Event:
    """Converts a wechatferry event to a nonebot event."""
    logger.debug(f"Converting message to event: {escape_tag(str(msg))}")
    if not msg:
        return None

    args = {
            "timestamp": msg.ts,
            "wx_type": msg.type,
            "from_wxid": msg.sender,
            "room_wxid": msg.roomid,
            "to_wxid": msg.roomid if msg.roomid else login_wx_id,
            "msgid": str(msg.id),
            "msg": msg.content,
            "at_user_list": __get_mention_list(msg),
            "to_me": not msg._is_group or msg.is_at(wcf.wxid),
            "raw_msg": msg.xml,
            "data": {}  # 抄的代码还没清楚这块干嘛的，先留着吧……
        }
    if msg.type == WxType.WX_MSG_TEXT:
        args['message'] = Message(MessageSegment.text(msg.content)),
    elif msg.type == WxType.WX_MSG_PICTURE:
        # 目前有bug，手动不点击图片的话，微信不会下载大图。。所以当前方法基本是废的
        args['message'] = Message(MessageSegment.image(file = msg.extra))
    elif msg.type == WxType.WX_MSG_VIDEO:
        # 同上。。。
        args['message'] = Message(MessageSegment.video(file = msg.extra))

    event_type = known_event_type.get(msg.type)
    if event_type is None:
        logger.warning(f"Unknown message type: {msg.type}")
        return None
    return event_type(**args)
