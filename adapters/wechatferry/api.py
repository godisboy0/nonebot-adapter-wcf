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
from .sqldb import database
from .utils import file_md5, logger
from .config import AdapterConfig

"""
发现绝大多数插件都是为 onebot.v11 所写，为了更好的复用（白嫖），这里也用 onebot.v11 中相关的数据结构。
参数约定:
to_wx_id: 群聊时为群聊id, 非群聊时为用户id
"""

user_cache = {}

md5_executor = ThreadPoolExecutor(max_workers=1)

class API:

    def __init__(self, wcf: Wcf, config: AdapterConfig):
        self.wcf = wcf
        self.config = config
        self.executor = ThreadPoolExecutor()

    def call_method_by_name(self, method_name, kwargs):
        method = getattr(self, method_name, None)
        if method is not None and callable(method):
            return method(**kwargs)
        else:
            raise ApiNotAvailable()

    async def call_api(self, api_name: str, kwargs: dict[str, Any]) -> None:
        """调用api"""
        return await asyncio.get_running_loop().run_in_executor(self.executor, self.call_method_by_name, api_name, kwargs)

    def send_text(self, to_wxid: str, text, **kwargs: dict[str, Any]) -> None:
        """发送文本消息"""
        if kwargs.get('aters'):
            self.wcf.send_text(
                text, to_wxid, aters=",".join(kwargs.get('aters')))
        else:
            self.wcf.send_text(text, to_wxid)

    def send_image(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送图片消息"""
        md5_executor.submit(record_md5, file, self.config)
        self.wcf.send_image(path=file, receiver=to_wxid)

    def send_music(self, to_wxid: str, **kwargs) -> None:
        """发送音乐消息"""
        if kwargs.get("audio"):
            md5_executor.submit(record_md5, kwargs.get('audio'), self.config)
            self.wcf.send_file(path=kwargs.get('audio'), receiver=to_wxid)

    def send_video(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送视频消息"""
        md5_executor.submit(record_md5, file, self.config)
        self.wcf.send_file(path=file, receiver=to_wxid)

    def send_file(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送文件消息"""
        md5_executor.submit(record_md5, file, self.config)
        self.wcf.send_file(path=file, receiver=to_wxid)

    def send_record(self, to_wxid: str, file, **kwargs: dict[str, Any]) -> None:
        """发送文件消息"""
        md5_executor.submit(record_md5, file, self.config)
        self.wcf.send_file(path=file, receiver=to_wxid)

    def send_wx_pat(self, to_wxid: str, **kwargs: dict[str, Any]) -> None:
        """发送拍一拍消息"""
        if kwargs.get('user_id'):
            self.wcf.send_pat_msg(to_wxid, kwargs.get('user_id'))
        else:
            logger.error("发送拍一拍消息失败，缺少 user_id 或者 to_wxid 不是群聊")

    def send_link(self, to_wxid: str, **kwargs: dict[str, Any]) -> None:
        """发送分享链接消息"""
        self.wcf.send_rich_text(
            kwargs.get('name'),
            kwargs.get('account'),
            kwargs.get('title'),
            kwargs.get('desc'),
            kwargs.get('url'),
            kwargs.get('thumburl'),
            to_wxid
        )

    def send_share(self, to_wxid: str, **kwargs: dict[str, Any]) -> None:
        """发送分享链接消息"""
        self.wcf.send_rich_text(
            kwargs.get('name'),     # 必然是None
            kwargs.get('account'),  # 必然是None
            kwargs.get('title'),
            kwargs.get('content'),
            kwargs.get('url'),
            kwargs.get('image'),
            to_wxid
        )

    def get_user_info(self, user_id: str, **kwargs: dict[str, Any]) -> UserInfo:
        """查询用户信息"""
        if not user_id:
            return UserInfo("", "", "", "")

        global user_cache
        if kwargs.get('refresh') or user_id not in user_cache:
            user_cache = {}
            for user in self.wcf.get_contacts():
                if user.get('wxid'):
                    user_cache[user['wxid']] = UserInfo(
                        wx_id=user['wxid'],
                        code=user.get('code', user['wxid']),
                        wx_name=user.get('name', user['wxid']),
                        gender=user.get('gender', "未知"),
                    )
                    if user.get('code'):
                        user_cache[user['code']] = user_cache[user['wxid']]
        return user_cache.get(user_id, UserInfo(user_id, user_id, user_id, "未知"))

    def get_alias_in_chatroom(self, group_id: str, user_id: str, **kwargs: dict[str, Any]) -> str:
        """查询群成员昵称"""
        return self.wcf.get_alias_in_chatroom(user_id, group_id) or user_id

def record_md5(file_path: str, config: AdapterConfig):
    DB = database(config.db_path)
    """记录文件的md5值"""
    if not (file_path.endswith(".jpg") or file_path.endswith(".png") or file_path.endswith(".jpeg") or file_path.endswith(".gif")):
        return
    try:
        md5 = file_md5(file_path)
        if md5:
            DB.insert('insert OR IGNORE into file_msg (type, msg_id_or_md5, file_path) values (?, ?, ?)', 'pic', md5, file_path)
    except Exception as e:
        logger.error(f"记录文件 {file_path} 的 MD5 值失败: {e}")