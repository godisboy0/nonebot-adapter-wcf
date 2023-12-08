from typing import Union, Any
from wcferry import WxMsg, Wcf
import os
import json
from .config import AdapterConfig
import time

base_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "data")
echo_temp_dir = os.path.join(base_dir, "echo_temp")

if not os.path.exists(echo_temp_dir):
    os.makedirs(echo_temp_dir, exist_ok=True)


def send_to_root(msg: Union[Any, WxMsg], wcf: Wcf = None, root_user: str = None):
    from nonebot import get_adapter, get_driver
    if wcf is None:
        wcf: Wcf = get_adapter().wcf
    if root_user is None:
        root_user = AdapterConfig.parse_obj(get_driver().config).root_user

    if isinstance(msg, WxMsg):
        file_str = json.dumps({
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
        }, ensure_ascii=False, indent=4)
        file_ext = "json"
    else:
        file_str = msg
        file_ext = "txt"
    if isinstance(msg, str) or isinstance(msg, WxMsg):
        file_path = os.path.join(
            echo_temp_dir, f'{int(time.time() * 1000)}.{file_ext}')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_str)
        wcf.send_file(file_path, root_user)
    else:
        raise TypeError(f"msg should be str or WxMsg, not {type(msg)}")
