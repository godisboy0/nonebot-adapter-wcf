"""
用于转换消息
"""
from typing import Dict, Callable, TypeVar, Optional, Any
from .message import MessageSegment, Message
from .sqldb import database
from wcferry import Wcf, WxMsg
from .type import WxType, WXSubType
from .utils import logger
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import shutil
import xml.etree.ElementTree as ET
from .utils import downloader


async def convert_to_bot_msg(msg: WxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Optional[Message]:
    """
    用于转换消息。转化为标准的 Message 类型。
    """
    msg_conv = msg_conv_dict.get(msg.type)
    if msg_conv:
        return await msg_conv(msg, bot_wx_id, wcf, db)
    else:
        logger.warning(f"Unknown msg type: {msg.type}")
        return None
    

MSG_CONV = TypeVar("MSG_CONV", bound=Callable[[
                   WxMsg, str, Wcf, database], Message])

msg_conv_dict: Dict[WxType, MSG_CONV] = {}

base_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "data")
pic_dir = os.path.join(base_dir, 'image')
voice_dir = os.path.join(base_dir, 'voice')
video_dir = os.path.join(base_dir, 'video')
file_dir = os.path.join(base_dir, 'file')

for p in [pic_dir, voice_dir, video_dir, file_dir]:
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)
download_executor = ThreadPoolExecutor(max_workers=5)


def msg_converter(wxtype: WxType, desc: str):
    logger.info(f"Registering wx_msg handler: {wxtype} {desc}")

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in wx_msg handler: {e}")
                return None
        msg_conv_dict[wxtype] = wrapper
        return wrapper
    return decorator


@msg_converter(WxType.WX_MSG_TEXT, "文本消息")
async def text_msg_handler(msg: WxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    content = re.sub(r'@.*?\u2005', '', msg.content).strip()
    content = re.sub(r'@.*? ', '', content).strip()
    content = re.sub(r'@.*?$', '', content).strip()
    return Message(MessageSegment.text(content))


@msg_converter(WxType.WX_MSG_PICTURE, "图片消息")
async def picture_msg_handler(msg: WxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    img_path = await asyncio.get_event_loop().run_in_executor(download_executor, wcf.download_image, msg.id, msg.extra, pic_dir, 30)
    if img_path:
        db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                  'pic', "MSG_ID_" + str(msg.id), img_path)
        return Message(MessageSegment.image(img_path))


@msg_converter(WxType.WX_MSG_VOICE, "语音消息")
async def voice_msg_handler(msg: WxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    voice_path = await asyncio.get_event_loop().run_in_executor(download_executor, wcf.get_audio_msg, msg.id, voice_dir, 30)
    if voice_path:
        db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                  'voice', "MSG_ID_" + str(msg.id), voice_path)
        return Message(MessageSegment.record(voice_path))


async def download_video(msg: WxMsg, wcf: Wcf) -> str:
    status = wcf.download_attach(msg.id, msg.thumb, msg.extra)
    if status == 0:
        for _ in range(60):
            raw_video_path = msg.thumb.split('.')[0] + '.mp4'
            new_vieo_path = os.path.join(video_dir, str(msg.id) + '.mp4')
            if os.path.exists(raw_video_path):
                shutil.copyfile(raw_video_path, new_vieo_path)
                return new_vieo_path
            else:
                await asyncio.sleep(0.5)
    else:
        return None


@msg_converter(WxType.WX_MSG_VIDEO, "视频消息")
async def video_msg_handler(msg: WxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    video_path = await download_video(msg, wcf)
    if video_path:
        db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                  'video', "MSG_ID_" + str(msg.id), video_path)
        return Message(MessageSegment.video(video_path))


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


@msg_converter(WxType.WX_MSG_REVOKE, "撤回消息")
async def revoke_msg_handler(msg: WxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    content = try_get_revoke_msg(msg.content)
    if content:
        return Message(MessageSegment('revoke', {'revoke_msg_id': content}))


@msg_converter(WxType.WX_MSG_APP, "应用消息")
async def app_msg_handler(msg: WxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    """
    虽然名为应用消息，但实际上是一堆消息的合体。
    所有我知道的类型都在 WXSubType 中。在这里再注册一堆 sub_msg_handler。
    """
    root = ET.fromstring(msg.content)
    subtype = int(root.find('appmsg/type').text)
    if subtype in sub_msg_conv_dict:
        simple_msg = SimpleWxMsg(msg.id, msg.thumb, msg.extra, msg.content)
        return await sub_msg_conv_dict[subtype](root, simple_msg, bot_wx_id, wcf, db)
    else:
        logger.warning(f"Unknown app msg type: {subtype}")
        return None

###########################
# 下面是各种应用消息的子消息的处理器
###########################


class SimpleWxMsg:

    def __init__(self, _id: int, thumb: str, extra: str, content: str):
        self.id = _id
        self.thumb = thumb
        self.extra = extra
        self.content = content


SUB_CONV = TypeVar("SUB_CONV", bound=Callable[[
                   ET.Element, SimpleWxMsg, str, Wcf, database], Message])
sub_msg_conv_dict: Dict[WXSubType, SUB_CONV] = {}


def sub_msg_converter(subtype: WXSubType, desc: str):
    logger.info(f"Registering sub_msg handler: {subtype} {desc}")

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in sub_msg handler: {e}")
                return None
        sub_msg_conv_dict[subtype] = wrapper
        return wrapper
    return decorator


async def build_link_message(root: ET.Element, msg_id: int, thumb: str = None) -> Message:
    title = root.find('appmsg/title').text
    desc = None if root.find(
        'appmsg/des') is None else root.find('appmsg/des').text
    url = root.find('appmsg/url').text
    if thumb:
        # 把 thumb 复制到 pic_path 下，然后返回路径(cache路径)
        extra_type = thumb.split('.')[-1]
        img_path = os.path.join(pic_dir, str(msg_id) + '.' + extra_type)
        for _ in range(60):
            if os.path.exists(thumb):
                break
            else:
                await asyncio.sleep(0.3)
        shutil.copyfile(thumb, img_path)
    elif (url_img_ele := root.find('appmsg/thumburl')) is not None:
        url_img = url_img_ele.text
        match = re.search(r'wxtype=([^&]*)', url_img)
        if match:
            wxtype = match.group(1)
            img_path = await asyncio.get_event_loop().run_in_executor(download_executor, downloader(url=url_img, file_name=f'{msg_id}.{wxtype}',  path=pic_dir).download)
        else:
            img_path = None
    else:
        img_path = None
    return Message(MessageSegment.share(
        title=title, content=desc, url=url, image=img_path))


@sub_msg_converter(WXSubType.WX_APPMSG_LINK, "链接消息")
async def link_msg_handler(root: ET.Element, msg: SimpleWxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    return await build_link_message(root, msg.id, msg.thumb)


@sub_msg_converter(WXSubType.WX_APPMSG_FILE, "文件消息")
async def file_msg_handler(root: ET.Element, msg: SimpleWxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    has_override_msg = root.find(
        'appmsg/appattach/overwrite_newmsgid') is not None
    if has_override_msg:
        if msg.extra is None:
            # 可能是从引用消息那里来的。
            file_name = None if root.find('appmsg/title') is None else root.find('appmsg/title').text
            _file_path = db.query(
                'select file_path from file_msg where msg_id_or_md5 = ?', "MSG_ID_" + str(msg.id))
            file_path = None if not _file_path else _file_path[0][0]
            if file_path:
                return Message(MessageSegment('file', {'file': file_path, "name": file_name}))
        for _ in range(60):
            if os.path.exists(msg.extra):
                file_path = os.path.join(file_dir, str(
                    msg.id) + '.' + msg.extra.split('.')[-1])
                shutil.copyfile(msg.extra, file_path)
                db.insert('insert into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)',
                          'file', "MSG_ID_" + str(msg.id), file_path)
                return Message(MessageSegment('file', {'file': file_path, "name": os.path.basename(msg.extra)}))
            else:
                await asyncio.sleep(0.3)
    else:
        return None


def extract_md5(content) -> Optional[str]:
    if not content:
        return None
    if 'md5="' not in content:
        return None
    content.split('md5="')[1].split('"')[0]


def try_get_file_path_from_db(speaker_id: str, bot_wx_id: str, refered_msg_id: int,
                              redered_content: str, db: database) -> Optional[str]:
    is_bot_sent = speaker_id == bot_wx_id
    msg_id_or_md5 = "MSG_ID_" + \
        str(refered_msg_id) if not is_bot_sent else extract_md5(redered_content)
    files = db.query(
        'select file_path from file_msg where type = "pic" and msg_id_or_md5 = ?', msg_id_or_md5)
    if files:
        return files[0][0]
    return None


@sub_msg_converter(WXSubType.WX_APPMSG_REFER, "引用消息")
async def refer_msg_handler(root: ET.Element, msg: SimpleWxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    """
    引用消息很复杂。包括：引用所有上述类型的消息。引用引用消息。引用聊天记录（multi_msg）。
    所有引用消息的格式重新标准化一下，标准化为：
    MessageSegment('wx_refer': {
        'content': content, # 表示引用消息的文本信息。
        'refered': {
            'id': msg_id,       # 表示被引用的消息的id。
            'time': timestamp,  # 表示被引用的消息的时间。
            'sender': wxid,     # 表示被引用的消息的发送者。
            'msg': Message,     # 表示被引用的消息。
        }
    })
    """
    # 这是引用消息的文本消息
    content = root.find('appmsg/title').text

    # 这是被引用的消息
    refered = root.find('appmsg/refermsg')
    refered_msg_id = int(refered.find('svrid').text)
    refered_msg_type = int(refered.find('type').text)
    refered_speaker_id = refered.find('fromusr').text
    refered_content = refered.find('content').text
    refered_createtime = int(refered.find('createtime').text)

    msg = None
    if refered_msg_type == WxType.WX_MSG_TEXT:
        # 引用了文本消息
        msg = Message(MessageSegment('wx_refer', {
            'content': content,
            'refered': {
                'id': refered_msg_id,
                'time': refered_createtime,
                'sender': refered_speaker_id,
                'msg': Message(MessageSegment.text(refered_content))
            }
        }))
    elif refered_msg_type == WxType.WX_MSG_PICTURE:
        pic_path = try_get_file_path_from_db(
            refered_speaker_id, bot_wx_id, refered_msg_id, refered_content, db)
        msg = Message(MessageSegment('wx_refer', {
            'content': content,
            'refered': {
                'id': refered_msg_id,
                'time': refered_createtime,
                'sender': refered_speaker_id,
                'msg': Message(MessageSegment.image(pic_path)) if pic_path else None
            }
        }))
    elif refered_msg_type == WxType.WX_MSG_VOICE:
        voice_path = try_get_file_path_from_db(
            refered_speaker_id, bot_wx_id, refered_msg_id, refered_content, db)
        msg = Message(MessageSegment('wx_refer', {
            'content': content,
            'refered': {
                'id': refered_msg_id,
                'time': refered_createtime,
                'sender': refered_speaker_id,
                'msg': Message(MessageSegment.record(voice_path)) if voice_path else None
            }
        }))
    elif refered_msg_type == WxType.WX_MSG_VIDEO:
        video_path = try_get_file_path_from_db(
            refered_speaker_id, bot_wx_id, refered_msg_id, refered_content, db)
        msg = Message(MessageSegment('wx_refer', {
            'content': content,
            'refered': {
                'id': refered_msg_id,
                'time': refered_createtime,
                'sender': refered_speaker_id,
                'msg': Message(MessageSegment.video(video_path)) if video_path else None
            }
        }))
    elif refered_msg_type == WxType.WX_MSG_APP:
        # 引用了应用消息，开始嵌套了，哦吼~
        refered_root = try_get_refer_root(refered_content)
        refered_subtype = int(refered_root.find('appmsg/type').text)
        if refered_subtype in sub_msg_conv_dict:
            inner_msg = await sub_msg_conv_dict[refered_subtype](refered_root, SimpleWxMsg(refered_msg_id, None, None, refered_content), bot_wx_id, wcf, db)
            msg = Message(MessageSegment('wx_refer', {
                'content': content,
                'refered': {
                    'id': refered_msg_id,
                    'time': refered_createtime,
                    'sender': refered_speaker_id,
                    'msg': inner_msg
                }
            }))

    return msg


@sub_msg_converter(WXSubType.WX_APPMSG_MUTIL, "聊天记录")
async def multi_msg_handler(root: ET.Element, msg: SimpleWxMsg, bot_wx_id: str, wcf: Wcf, db: database) -> Message:
    """
    这块是聊天记录。多个消息的聚合。所以可能聚合上面的所有消息。
    """
    recorditem = root.find('appmsg/recorditem')
    if recorditem is None:
        return None
    nested_xml = ET.fromstring(recorditem.text)

    datalist = nested_xml.findall('datalist/dataitem')
    if datalist is None:
        return None

    msg_list: list[Dict[str, Any]] = []
    for dataitem in datalist:
        datatype = dataitem.get('datatype')
        handler = multi_msg_handlers.get(int(datatype))
        if not handler:
            logger.warning(
                f"Unsupported multi message type: {datatype}, dataitem: {dataitem}")
            continue
        single_data = await handler(dataitem, bot_wx_id, db)
        if single_data is not None:
            msg_list.append(single_data)

    return Message(MessageSegment('wx_multi', {'msg_list': msg_list}))


###########################
# 下面是聊天记录的处理器
# 聊天记录又是不同的datatype。。。很麻烦。
###########################

multi_msg_handlers: Dict[int, Callable] = {}


def multi_msg_handler(datatype: int, desc: str):
    logger.info(f"Registering multi_msg_handler: {datatype} {desc}")

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in multi_msg_handler: {e}")
                return None
        multi_msg_handlers[datatype] = wrapper
        return wrapper
    return decorator


@multi_msg_handler(2, "图片消息")
def multi_handle_image_msg(data: ET.Element, login_bot_id: str, db: database) -> Dict[str, Any]:
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    fullmd5 = data.find("fullmd5").text                 # 图片MD5
    _pic_path = db.query('select file_path from file_msg where msg_id_or_md5 = ? or msg_id_or_md5 = ?',
                         "MSG_ID_" + str(fromnewmsgid), fullmd5)
    pic_path = None if not _pic_path else _pic_path[0][0]
    data = {
        'id': fromnewmsgid,
        'time': sourcetime,
        'sender': sourcename,
        'msg': Message(MessageSegment.image(pic_path)) if pic_path else None
    }
    return data


@multi_msg_handler(5, "链接消息")
def multi_handle_link_msg(data: ET.Element, login_bot_id: str, db: database) -> Dict[str, Any]:
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    weburlitem = data.find("weburlitem")                # 链接详情
    title = weburlitem.find("title").text               # 标题
    link = weburlitem.find("link").text                 # 链接
    return {
        'id': fromnewmsgid,
        'time': sourcetime,
        'sender': sourcename,
        'msg': Message(MessageSegment.share(
            link, title, None, None
        ))
    }


@multi_msg_handler(4, "视频消息")
def multi_handle_video_msg(data: ET.Element, login_bot_id: str, db: database) -> Dict[str, Any]:
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    fullmd5 = data.find("fullmd5").text                 # 视频MD5
    _video_path = db.query('select file_path from file_msg where msg_id_or_md5 = ? or msg_id_or_md5 = ?',
                           "MSG_ID_" + str(fromnewmsgid), fullmd5)
    video_path = None if not _video_path else _video_path[0][0]

    return {
        'id': fromnewmsgid,
        'time': sourcetime,
        'sender': sourcename,
        'msg': Message(MessageSegment.video(video_path)) if video_path else None
    }


@multi_msg_handler(8, "文件消息")
def multi_handle_file_msg(data: ET.Element, login_bot_id: str, db: database) -> Dict[str, Any]:
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    fullmd5 = data.find("fullmd5").text                 # 文件MD5
    datatitle = data.find("datatitle").text             # 文件名
    _file_path = db.query('select file_path from file_msg where msg_id_or_md5 = ? or msg_id_or_md5 = ?',
                          "MSG_ID_" + str(fromnewmsgid), fullmd5)
    file_path = None if not _file_path else _file_path[0][0]
    return {
        'id': fromnewmsgid,
        'time': sourcetime,
        'sender': sourcename,
        'msg': Message(MessageSegment('file', {'file': file_path, "name": datatitle})) if file_path else None
    }


@multi_msg_handler(1, "字面值消息")
def multi_handle_text_msg(data: ET.Element, login_bot_id: str, db: database) -> Dict[str, Any]:
    """
    所有的文本消息，都是这个类型。包括：
    1. 文本消息；
    2. 语音消息；（实际上会转成一个 [Audio] 3" 文本）
    3. 引用消息：会显示引用的字面内容，并且包含 refermsgitem 信息。
    """
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    refermsgitem = data.find("refermsgitem")            # 引用消息详情
    if refermsgitem is not None:
        # refered_type = refermsgitem.find("type").text       # 引用消息类型
        refered_id = refermsgitem.find("svrid").text        # 引用消息ID
        refered_content = refermsgitem.find(
            "content").text  # 引用消息内容，又是个新的嵌套xml
        # datadesc = refermsgitem.find("datadesc").text
        refered_root = try_get_refer_root(refered_content)

        inner_msg = refer_msg_handler(refered_root, SimpleWxMsg(
            refered_id, None, None, refered_content), login_bot_id, None, db)
        return {
            'id': fromnewmsgid,
            'time': sourcetime,
            'sender': sourcename,
            'msg': inner_msg
        }
    else:  # 语音消息 或者 纯文本消息
        datadesc = data.find("datadesc").text
        return {
            'id': fromnewmsgid,
            'time': sourcetime,
            'sender': sourcename,
            'msg': Message(MessageSegment.text(datadesc))
        }


def try_get_refer_root(content: str) -> Optional[ET.Element]:
    try:
        root = ET.fromstring(content)
        return root
    except ET.ParseError:
        import html
        try:
            content = html.unescape(content)
            root = ET.fromstring(content)
            return root
        except ET.ParseError:
            return None
