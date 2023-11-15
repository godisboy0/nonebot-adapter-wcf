from wcferry import Wcf, WxMsg
from .event import Event, PrivateMessageEvent, GroupMessageEvent, Sender
from .message import MessageSegment, Message
from .type import WxType
from .utils import logger
import re
from nonebot.utils import escape_tag
import xml.etree.ElementTree as ET
from typing import Optional

"""
onebot11标准要求：https://github.com/botuniverse/onebot-11/blob/master/README.md
"""

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

    args = {}
    if msg.type == WxType.WX_MSG_TEXT:
        content = re.sub(r'@.*?\u2005', '', msg.content).strip()
        content = re.sub(r'@.*? ', '', content).strip()
        content = re.sub(r'@.*?$', '', content).strip()
        args['message'] = Message(MessageSegment.text(content))
    elif msg.type == WxType.WX_MSG_REVOKE:
        content = try_get_revoke_msg(msg.content)
        if content:
            args['message'] = Message(MessageSegment('revoke', {'revoke_msg_id': content}))
        else:
            return None

    else:
        return None
    args['original_message'] = args["message"]

    args.update({
        "post_type": "message",
        "time": msg.ts,
        "wx_type": msg.type,
        "self_id": login_wx_id,
        "user_id": msg.sender,
        "message_id": msg.id,
        "raw_message": msg.xml,
        "font": 12,     # meaningless for wechat, but required by onebot 11
        "sender": Sender(user_id=msg.sender),
        "to_me": (not msg._is_group) or msg.is_at(login_wx_id),
    })

    if msg.roomid:  # 群消息
        at_users = __get_mention_list(msg)
        args['message'] = args['message'] + [MessageSegment.at(
            user_id) for user_id in at_users]
        args['original_message'] = args["message"]
        args.update({
            "message_type": "group",
            "sub_type": "normal",
            "group_id": msg.roomid
        })
        return GroupMessageEvent(**args)
    else:
        args.update({
            "message_type": "private",
            "sub_type": "friend"
        })
        return PrivateMessageEvent(**args)

def try_get_revoke_msg(content: str) -> Optional[str]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None
    
    msg_sub_type = root.attrib.get('type')
    if msg_sub_type != 'revokemsg':
        return None
    
    newmsgid_element = root.find('revokemsg/newmsgid')
    return newmsgid_element.text if newmsgid_element is not None else None