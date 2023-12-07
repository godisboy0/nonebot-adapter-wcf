from wcferry import Wcf, WxMsg
from .event import Event, PrivateMessageEvent, GroupMessageEvent, Sender
from .message import MessageSegment, Message
from .type import WxType, WXSubType
from .utils import logger
import re
from nonebot.utils import escape_tag
from typing import Optional
import os
from concurrent.futures import ThreadPoolExecutor
import asyncio
import xml.etree.ElementTree as ET
from .sqldb import database
import html
from .utils import downloader
import shutil
from .multi_msg_handlers import multi_msg_handlers

"""
onebot11标准要求：https://github.com/botuniverse/onebot-11/blob/master/README.md
onebot11 message segment 类型: https://github.com/botuniverse/onebot-11/blob/master/message/segment.md
"""

base_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "data")
pic_path = os.path.join(base_dir, 'image')
voice_dir_path = os.path.join(base_dir, 'voice')
video_dir_path = os.path.join(base_dir, 'video')
file_dir_path = os.path.join(base_dir, 'file')

for p in [pic_path, voice_dir_path, video_dir_path, file_dir_path]:
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
    if not msg or msg.type == WxType.WX_MSG_HEARTBEAT:
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
    elif msg.type == WxType.WX_MSG_PICTURE:
        img_path = await asyncio.get_event_loop().run_in_executor(download_executor, wcf.download_image, msg.id, msg.extra, pic_path, 30)
        if img_path:
            db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                      'pic', "MSG_ID_" + str(msg.id), img_path)
            args['message'] = Message(MessageSegment.image(img_path))
    elif msg.type == WxType.WX_MSG_VOICE:
        file_path = await asyncio.get_event_loop().run_in_executor(download_executor, wcf.get_audio_msg, msg.id, voice_dir_path, 30)
        if file_path:
            db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                      'voice', "MSG_ID_" + str(msg.id), file_path)
            args['message'] = Message(MessageSegment.record(file_path))
    elif msg.type == WxType.WX_MSG_VIDEO:
        # 这里实际可以下载。但是status返回以后，不代表下载实际完成，需要搞个监听，等到文件出现了，再返回。
        # 和 thumb 在一个文件夹。但名字是后缀改成.mp4
        video_msg = await build_video_message(msg, login_wx_id, wcf)
        if video_msg is not None:
            db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                      'voice', "MSG_ID_" + str(msg.id), file_path)
            args['message'] = video_msg
    elif msg.type == WxType.WX_MSG_APP:
        # xml 内部有个type字段，标志了子类型
        # type = 57 引用消息，这里作为一种扩展类型。
        root = ET.fromstring(msg.content)
        subtype = int(root.find('appmsg/type').text)
        if subtype == WXSubType.WX_APPMSG_REFER:
            refer_msg = await build_refer_message(root, login_wx_id, db)
            if refer_msg:
                args['message'] = refer_msg
        elif subtype == WXSubType.WX_APPMSG_LINK:
            # extra 就是 pic
            link_msg = await build_link_message(root, msg_id=msg.id, thumb = msg.thumb)
            if link_msg:
                args['message'] = link_msg
        elif subtype == WXSubType.WX_APPMSG_FILE:
            # 文件会触发两次消息，第一次是文件发出消息，第二次是文件上传完成消息。一般来说，我们需要上传完成消息，因为这样这边才开始下载
            # 引用一个尚未上传完毕的消息时，refer_msg_id是第一个消息，引用上传完毕的消息时，refer_msg_id是第二个消息。
            # 但是在文件很小的情况下，这俩消息也就接近于同时到达了，而且文件都下载好了，于是会触发两次下载，并且都会发出带文件的消息，这很不好，我们粗暴地忽略第一条消息。
            # 第二条消息会有一个 overwrite_newmsgid 字段，如果存在，说明是第二条消息，否则是第一条消息。
            has_override_msg = root.find('appmsg/appattach/overwrite_newmsgid') is not None
            if has_override_msg:
                for _ in range(60):
                    if os.path.exists(msg.extra):
                        file_path = os.path.join(file_dir_path, str(msg.id) + '.' + msg.extra.split('.')[-1])
                        shutil.copyfile(msg.extra, file_path)
                        db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                                    'file', "MSG_ID_" + str(msg.id), file_path)
                        args['message'] = Message(MessageSegment('file', {'file': file_path}))
                        break
                    else:
                        await asyncio.sleep(0.3)
        elif subtype == WXSubType.WX_APPMSG_MUTIL:
            # 合并消息，也就是聊天记录。。非常复杂。先尽量处理了我能处理的吧。
            multi_message = extract_multi_message(root, login_wx_id, db)
            args['message'] = multi_message

    if args.get('message') is None:
        return None
    
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


async def build_video_message(msg: WxMsg, wcf: Wcf) -> Message:
    status = wcf.download_attach(msg.id, msg.thumb, msg.extra)
    if status == 0:
        for _ in range(60):
            raw_video_path = msg.thumb.split('.')[0] + '.mp4'
            new_vieo_path = os.path.join(video_dir_path, str(msg.id) + '.mp4')
            if os.path.exists(raw_video_path):
                shutil.copyfile(raw_video_path, new_vieo_path)
                return Message(MessageSegment.video(new_vieo_path))
            else:
                await asyncio.sleep(0.5)
    else:
        return None


async def build_link_message(root: ET.Element, msg_id: int, thumb: str = None) -> Message:
    title = root.find('appmsg/title').text
    desc = None if root.find('appmsg/des') is None else root.find('appmsg/des').text
    url = root.find('appmsg/url').text
    if thumb:
        # 把 thumb 复制到 pic_path 下，然后返回路径(cache路径)
        extra_type = thumb.split('.')[-1]
        img_path = os.path.join(pic_path, str(msg_id) + '.' + extra_type)
        for _ in range(60):
            if os.path.exists(thumb):
                break
            else:
                await asyncio.sleep(0.3)
        shutil.copyfile(thumb, img_path)
    elif (url_img_ele:= root.find('appmsg/thumburl')) is not None:
        url_img = url_img_ele.text
        match = re.search(r'wxtype=([^&]*)', url_img)
        if match:
            wxtype = match.group(1)
            img_path = await asyncio.get_event_loop().run_in_executor(download_executor, downloader(url=url_img, file_name=f'{msg_id}.{wxtype}',  path=pic_path).download)
        else:
            img_path = None
    else:
        img_path = None
    return Message(MessageSegment.share(
        title=title, content=desc, url=url, image=img_path))


async def build_refer_message(root: ET.Element, login_wx_id: str, db: database) -> Message:
    """
    从引用消息中解析出引用的内容。
    目前仅支持引用文本消息和图片消息。
    """
    try:
        msg = None
        refer_msg_id = int(root.find('appmsg/refermsg/svrid').text)
        refer_msg_type = int(root.find('appmsg/refermsg/type').text)
        content = root.find('appmsg/title').text
        speaker_id = root.find('appmsg/refermsg/fromusr').text
        refer_content = root.find('appmsg/refermsg/content').text
        if refer_msg_type == WxType.WX_MSG_TEXT:
            # 引用了文本消息
            msg = Message(MessageSegment('wx_refer', {
                'content': content,
                'refer': {
                    'id': refer_msg_id,
                    'type': 'text',
                    'speaker_id': speaker_id,
                    'content': refer_content
                }
            }))
        elif refer_msg_type == WxType.WX_MSG_PICTURE:
            # 引用了图片消息
            is_bot_sent = speaker_id == login_wx_id
            if not is_bot_sent:
                msg_id_or_md5 = "MSG_ID_" + str(refer_msg_id)
            else:
                msg_id_or_md5 = extract_md5(refer_content)
            pics = db.query(
                'select file_path from file_msg where type = "pic" and msg_id_or_md5 = ?', msg_id_or_md5)
            if pics:
                pic_path = pics[0][0]
            else:
                # 这里实际上可以再触发一次下载，但是还要看看extra怎么从MSGX.db中获取。。再说吧再说吧。。。
                pic_path = None
            msg = Message(MessageSegment('wx_refer', {
                'content': content,
                'refer': {
                    'id': refer_msg_id,
                    'type': 'image',
                    'speaker_id': speaker_id,
                    'content': pic_path
                }
            }))
        elif refer_msg_type == WxType.WX_MSG_VIDEO:
            # 引用了视频消息
            is_bot_sent = speaker_id == login_wx_id
            if not is_bot_sent:
                msg_id_or_md5 = "MSG_ID_" + str(refer_msg_id)
            else:
                msg_id_or_md5 = extract_md5(refer_content)
            videos = db.query(
                'select file_path from file_msg where type = "video" and msg_id_or_md5 = ?', msg_id_or_md5)
            if videos:
                video_path = videos[0][0]
            else:
                # 这里实际上可以再触发一次下载，但是还要看看extra怎么从MSGX.db中获取。。再说吧再说吧。。。
                video_path = None
            msg = Message(MessageSegment('wx_refer', {
                'content': content,
                'refer': {
                    'id': refer_msg_id,
                    'type': 'video',
                    'speaker_id': speaker_id,
                    'content': video_path
                }
            }))
        elif refer_msg_type == WxType.WX_MSG_VOICE:
            # 引用了语音消息
            is_bot_sent = speaker_id == login_wx_id
            if not is_bot_sent:
                msg_id_or_md5 = "MSG_ID_" + str(refer_msg_id)
            else:
                msg_id_or_md5 = extract_md5(refer_content)
            voices = db.query(
                'select file_path from file_msg where type = "voice" and msg_id_or_md5 = ?', msg_id_or_md5)
            if voices:
                voice_path = voices[0][0]
            else:
                voice_path = None
            msg = Message(MessageSegment('wx_refer', {
                'content': content,
                'refer': {
                    'id': refer_msg_id,
                    'type': 'voice',
                    'speaker_id': speaker_id,
                    'content': voice_path
                }
            }))
        elif refer_msg_type == WxType.WX_MSG_APP:
            # 引用了应用消息，可能是个引用。我这里直接判断下，把引用消息进一步解析，读出其中的文本，作为回复一个文本信息返回。
            refer_root = try_get_refer_root(refer_content)
            if refer_root is None:
                return None
            refered_subtype = int(refer_root.find('appmsg/type').text)
            if refered_subtype == WXSubType.WX_APPMSG_REFER:
                inner_refer_content = refer_root.find('appmsg/title').text
                msg = Message(MessageSegment('wx_refer', {
                    'content': content,
                    'refer': {
                        'id': refer_msg_id,
                        'type': 'refer',
                        'speaker_id': speaker_id,
                        'content': inner_refer_content
                    }
                }))
            elif refered_subtype == WXSubType.WX_APPMSG_LINK:
                refered_link_msg: Message = await build_link_message(
                    refer_root, msg_id=refer_msg_id)
                msg = Message(MessageSegment('wx_refer', {
                    'content': content,
                    'refer': {
                        'id': refer_msg_id,
                        'type': 'link',
                        'speaker_id': speaker_id,
                        'content': refered_link_msg[0].data
                    }
                }))
            elif refered_subtype == WXSubType.WX_APPMSG_FILE:
                # 忽略对第一个文件的引用。
                has_override_msg = refer_root.find(
                    'appmsg/appattach/overwrite_newmsgid') is not None
                if not has_override_msg:
                    return None
                file_path = os.path.join(file_dir_path, str(refer_msg_id) + '.' + refer_root.find('appmsg/appattach/fileext').text)
                if not os.path.exists(file_path):
                    file_path = None
                msg = Message(MessageSegment('wx_refer', {
                    'content': content,
                    'refer': {
                        'id': refer_msg_id,
                        'type': 'file',
                        'speaker_id': speaker_id,
                        'content': file_path
                    }
                }))

        return msg
    except Exception as e:
        logger.error(f"Failed to build reply message: {e}")
        return None


def try_get_refer_root(content: str) -> Optional[ET.Element]:
    try:
        root = ET.fromstring(content)
        return root
    except ET.ParseError:
        try:
            content = html.unescape(content)
            root = ET.fromstring(content)
            return root
        except ET.ParseError:
            return None


def extract_md5(content) -> Optional[str]:
    if not content:
        return None
    if 'md5="' not in content:
        return None
    content.split('md5="')[1].split('"')[0]


async def extract_multi_message(root: ET.Element, login_wx_id: str, db: database) -> Message:
    """
    从合并消息中解析出消息内容。
    """
    recorditem = root.find('appmsg/recorditem')
    if recorditem is None:
        return None
    nested_xml = ET.fromstring(recorditem.text)

    datalist = nested_xml.findall('datalist/dataitem')
    if datalist is None:
        return None
    
    for dataitem in datalist:
        datatype = dataitem.get('datatype')
        handler = multi_msg_handlers.get(int(datatype))
        if not handler:
            logger.warning(f"Unsupported multi message type: {datatype}, dataitem: {dataitem}")
            continue
        msg = await handler(dataitem, login_wx_id, db)
