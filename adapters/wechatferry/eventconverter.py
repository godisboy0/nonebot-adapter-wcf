from wcferry import Wcf, WxMsg
from .event import Event, PrivateMessageEvent, GroupMessageEvent, Sender
from .message import MessageSegment, Message
from .type import WxType
from .utils import logger
import re
from nonebot.utils import escape_tag
import xml.etree.ElementTree as ET
from typing import Optional
import os
from concurrent.futures import ThreadPoolExecutor
import asyncio
import xml.etree.ElementTree as ET
from .sqldb import database

"""
onebot11标准要求：https://github.com/botuniverse/onebot-11/blob/master/README.md
"""

base_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "data")
pic_path = os.path.join(base_dir, 'image')

for p in [pic_path]:
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)

download_executor = ThreadPoolExecutor(max_workers=5)


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
            args['message'] = Message(MessageSegment(
                'revoke', {'revoke_msg_id': content}))
        else:
            return None
    elif msg.type == WxType.WX_MSG_PICTURE:
        global pic_path
        img_path = await asyncio.get_event_loop().run_in_executor(download_executor, wcf.download_image, msg.id, msg.extra, pic_path)
        if img_path:
            db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)', 'pic', "MSG_ID_" + str(msg.id), img_path)
            args['message'] = Message(MessageSegment.image(img_path))
        else:
            return None
    elif msg.type == WxType.WX_MSG_APP:
        # xml 内部有个type字段，标志了子类型
        # type = 57 引用消息，这里作为一种扩展类型。
        root = ET.fromstring(msg.content)
        type_field = root.find('appmsg/type')
        if type_field is not None:
            type = type_field.text
            if type == '57':
                msg = build_quote_message(root, login_wx_id, db)
                if msg:
                    args['message'] = msg
                else:
                    return None
            else:
                return None    # 暂时不支持其他类型的app消息
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


def build_quote_message(root: ET.Element, login_wx_id: str, db: database) -> Message:
    """
    从引用消息中解析出引用的内容。
    目前仅支持引用文本消息和图片消息。
    """
    try:
        quote_msg_id = int(root.find('appmsg/refermsg/svrid').text)
        quote_msg_type = int(root.find('appmsg/refermsg/type').text)
        content = root.find('appmsg/title').text
        speaker_id = root.find('appmsg/refermsg/fromusr').text
        content = root.find('appmsg/refermsg/content').text
        if quote_msg_type == 1:
            # 引用了文本消息
            msg = Message(MessageSegment('wx_quote', {
                'content': content,
                'quote': {
                    'id': quote_msg_id,
                    'type': 'text',
                    'speaker_id': speaker_id,
                    'content': content
                }
            }))
        elif quote_msg_type == 3:
            # 引用了图片消息
            is_bot_sent = speaker_id == login_wx_id
            if not is_bot_sent:
                msg_id_or_md5 = "MSG_ID_" + str(quote_msg_id)
            else:
                msg_id_or_md5 = extract_md5(content)
            pics = db.query(
                'select file_path from file_msg where type = "pic" and msg_id_or_md5 = ?', msg_id_or_md5)
            if pics:
                pic_path = pics[0][0]
            msg = Message(MessageSegment('wx_quote', {
                'content': content,
                'quote': {
                    'id': quote_msg_id,
                    'type': 'image',
                    'speaker_id': speaker_id,
                    'content': pic_path
                }
            }))
        
        return msg
    except Exception as e:
        logger.error(f"Failed to build reply message: {e}")
        return None


def extract_md5(content) -> Optional[str]:
    if not content:
        return None
    if 'md5="' not in content:
        return None
    content.split('md5="')[1].split('"')[0]
