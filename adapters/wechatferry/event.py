from nonebot.adapters.onebot.v11 import (
    Event,
    MessageEvent,
    PrivateMessageEvent as OnebotPrivateMessageEvent,
    GroupMessageEvent as OnebotGroupMessageEvent
)
from nonebot.adapters.onebot.v11.event import Sender as OnebotSender

class Sender (OnebotSender):
    user_id: str # 微信的用户 ID

class PrivateMessageEvent (OnebotPrivateMessageEvent):
    self_id: str # 登录的微信 ID，因为并非int，只好重写一下
    user_id: str # 微信的用户 ID

class GroupMessageEvent (OnebotGroupMessageEvent):
    self_id: str # 登录的微信 ID，因为并非int，只好重写一下
    user_id: str # 微信的用户 ID
    group_id: str # 微信的群组 ID

__all__ = [
    "Event",
    "MessageEvent",
    "PrivateMessageEvent",
    "GroupMessageEvent"
]
from pydantic import BaseModel

class TTT(BaseModel):
    user_id: int

class TTTB(TTT):
    user_id: str

if __name__=="__main__":
    f = TTT.parse_obj({"user_id":123})
    f2 = TTTB.parse_obj({"user_id":"你好"})
    print(f.user_id)
    print(f2.user_id)