
from typing import Dict, Callable
from .sqldb import database
from xml.etree import ElementTree as ET
from .utils import logger

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
def handle_image_msg(data: ET.Element, login_bot_id: str, db: database):
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间
    
    fullmd5 = data.find("fullmd5").text                 # 图片MD5
    _pic_path = db.query('select file_path from file_msg where msg_id_or_md5 = ? or msg_id_or_md5 = ?',
                        "MSG_ID_" + str(fromnewmsgid), fullmd5)
    pic_path = None if not _pic_path else _pic_path[0][0]
    return {
        "type": "image",
        "msg_id": fromnewmsgid,
        "sender": sourcename,
        "sendtime": sourcetime,
        "content": {
            "file_path": pic_path,
        }
    }

@multi_msg_handler(5, "链接消息")
def handle_link_msg(data: ET.Element, login_bot_id: str, db: database):
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    weburlitem = data.find("weburlitem")                # 链接详情
    title = weburlitem.find("title").text               # 标题
    link = weburlitem.find("link").text                 # 链接
    thumburl = weburlitem.find("thumburl").text         # 缩略图链接
    return {
        "type": "link",
        "msg_id": fromnewmsgid,
        "sender": sourcename,
        "sendtime": sourcetime,
        "content": {
            "title": title,
            "link": link,
            "thumburl": thumburl,
        }
    }

@multi_msg_handler(4, "视频消息")
def handle_video_msg(data: ET.Element, login_bot_id: str, db: database):
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    fullmd5 = data.find("fullmd5").text                 # 视频MD5
    _video_path = db.query('select file_path from file_msg where msg_id_or_md5 = ? or msg_id_or_md5 = ?',
                        "MSG_ID_" + str(fromnewmsgid), fullmd5)
    video_path = None if not _video_path else _video_path[0][0]
    return {
        "type": "video",
        "msg_id": fromnewmsgid,
        "sender": sourcename,
        "sendtime": sourcetime,
        "content": {
            "file_path": video_path,
        }
    }

@multi_msg_handler(8, "文件消息")
def handle_file_msg(data: ET.Element, login_bot_id: str, db: database):
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    fullmd5 = data.find("fullmd5").text                 # 文件MD5
    datatitle = data.find("datatitle").text             # 文件名
    _file_path = db.query('select file_path from file_msg where msg_id_or_md5 = ? or msg_id_or_md5 = ?',
                        "MSG_ID_" + str(fromnewmsgid), fullmd5)
    file_path = None if not _file_path else _file_path[0][0]
    return {
        "type": "file",
        "msg_id": fromnewmsgid,
        "sender": sourcename,
        "sendtime": sourcetime,
        "content": {
            "file_path": file_path,
            "file_name": datatitle,
        }
    }

"""
所有的文本消息，都是这个类型。包括：
1. 文本消息；
2. 语音消息；（实际上会转成一个 [Audio] 3" 文本）
3. 引用消息：会显示引用的字面内容，并且包含 refermsgitem 信息。
"""
@multi_msg_handler(1, "引用消息")
def handle_refer_msg(data: ET.Element, login_bot_id: str, db: database):
    fromnewmsgid = data.find("fromnewmsgid").text       # 原始消息ID
    sourcename = data.find("sourcename").text           # 发送人昵称
    sourcetime = data.find("sourcetime").text           # 发送时间

    refermsgitem = data.find("refermsgitem")            # 引用消息详情
    if refermsgitem is not None:
        refered_type = refermsgitem.find("type").text       # 引用消息类型
        refered_id = refermsgitem.find("svrid").text        # 引用消息ID
        refered_content = refermsgitem.find("content").text # 引用消息内容，又是个新的嵌套xml
        datadesc = refermsgitem.find("datadesc").text       # 引用消息描述
        return {
            "type": "refer",
            "msg_id": fromnewmsgid,
            "sender": sourcename,
            "sendtime": sourcetime,
            "content": {
                "msgtype": refered_type,
                "msg_id": refered_id,
                "text": datadesc,
                "content": {
                    # TODO 
                }
            }
        }
    
    # 没有引用消息，查一下消息表看看

