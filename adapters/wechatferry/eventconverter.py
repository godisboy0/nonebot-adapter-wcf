from wcferry import Wcf, WxMsg
from .event import Event, PrivateMessageEvent, GroupMessageEvent, Sender
from .message import MessageSegment, Message
from .type import WxType
from .utils import logger
import re
from nonebot.utils import escape_tag
import os
from .sqldb import database
from .msg_converters import convert_to_bot_msg

"""
onebot11标准要求：https://github.com/botuniverse/onebot-11/blob/master/README.md
onebot11 message segment 类型: https://github.com/botuniverse/onebot-11/blob/master/message/segment.md
"""

base_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "data")
echo_temp_dir = os.path.join(base_dir, "echo_temp")

if not os.path.exists(echo_temp_dir):
    os.makedirs(echo_temp_dir, exist_ok=True)


async def echo_root_msg_as_json_file(msg: WxMsg, wcf: Wcf):
    from nonebot import get_driver
    root_user = get_driver().config.root_user
    echo_root_msg = get_driver().config.echo_root_msg
    if msg.sender != root_user or not echo_root_msg or msg._is_group:
        return
    
    import json    
    file_path = os.path.join(echo_temp_dir, f'{msg.id}.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({
            'is_self': msg._is_self,
            'is_group': msg._is_group,
            'type': msg.type,
            'id': msg.id,
            'ts': msg.ts,
            'sign': msg.sign,
            'xml': msg.xml.replace("\n", "").replace("\t", "") if msg.xml else None,
            'sender': msg.sender,
            'roomid': msg.roomid,
            'content': msg.content.replace("\n", "").replace("\t", "") if msg.content else None,
            'thumb': msg.thumb,
            'extra': msg.extra
        }, f, ensure_ascii=False, indent=4)
    wcf.send_file(file_path, root_user)


def __get_mention_list(req: WxMsg) -> list[str]:
    if req.xml is not None:
        pattern = r'<atuserlist>(.*?)</atuserlist>'
        match = re.search(pattern, req.xml)
        if match:
            atuserlist = match.group(1)
            return [user_id for user_id in atuserlist.split(',')]
    return []


async def convert_to_event(msg: WxMsg, login_wx_id: str, wcf: Wcf, db: database) -> Event:
    """Converts a wechatferry event to a nonebot event."""
    logger.debug(f"Converting message to event: {escape_tag(str(msg))}")
    if not msg or msg.type == WxType.WX_MSG_HEARTBEAT:
        return None
    
    await echo_root_msg_as_json_file(msg, wcf)

    args = {}
    onebot_msg: Message = await convert_to_bot_msg(msg, login_wx_id, wcf, db)
    if onebot_msg is None:
        return None
    
    args['message'] = onebot_msg
    args['original_message'] = args["message"]

    args.update({
        "post_type": "message",
        "time": msg.ts,
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
