"""
所有的 api 都定义在这里。
call_api 的所有方法最终都会调用这里的方法。
"""
from wcferry import Wcf
from typing import Any
from .exception import ApiNotAvailable
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .basemodel import UserInfo
from typing import Optional

"""
发现绝大多数插件都是为 onebot.v11 所写，为了更好的复用（白嫖），这里也用 onebot.v11 中相关的数据结构。
参数约定:
to_wx_id: 群聊时为群聊id, 非群聊时为用户id
"""

user_cache = {}

class API:

    def call_method_by_name(self, method_name, kwargs):
        method = getattr(self, method_name, None)
        if method is not None and callable(method):
            return method(**kwargs)
        else:
            raise ApiNotAvailable()

    async def call_api(self, api_name: str, kwargs: dict[str, Any]) -> None:
        """调用api"""
        await asyncio.get_running_loop().run_in_executor(self.executor, self.call_method_by_name, api_name, kwargs)

    def __init__(self, wcf: Wcf):
        self.wcf = wcf
        self.executor = ThreadPoolExecutor()

    def send_text(self, to_wxid: str, text, **kwargs: dict[str, Any]) -> None:
        """发送文本消息"""
        if kwargs.get('aters'):
            self.wcf.send_text(text, to_wxid, aters=",".join(kwargs.get('aters')))
        else:
            self.wcf.send_text(text, to_wxid)

    def send_image(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送图片消息"""
        self.wcf.send_image(path=file, receiver=to_wxid)

    def send_music(self, to_wxid: str, **kwargs) -> None:
        """发送音乐消息"""
        if kwargs.get("audio"):
            self.wcf.send_file(path=kwargs.get('audio'), receiver=to_wxid)

    def send_video(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送视频消息"""
        self.wcf.send_file(path=file, receiver=to_wxid)

    def send_file(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送文件消息"""
        self.wcf.send_file(path=file, receiver=to_wxid)

    def send_record(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送文件消息"""
        self.wcf.send_file(path=file, receiver=to_wxid)

    def get_user_info(self, user_id: str, **kwargs: dict[str, Any]) -> Optional[UserInfo]:
        """查询用户信息"""
        if not user_id:
            return None
        
        global user_cache
        if kwargs.get('refresh') or user_id not in user_cache:
            user_cache = {}
            for user in self.wcf.get_user_list():
                user_cache[user['wxid']] = user
        return user_cache.get(user_id)
    
    def get_alias_in_chatroom(self, group_id: str, user_id: str, **kwargs: dict[str, Any]) -> str:
        """查询群成员昵称"""
        return self.wcf.get_alias_in_chatroom(group_id, user_id) or user_id