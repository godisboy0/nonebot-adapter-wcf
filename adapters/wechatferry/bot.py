import asyncio
import re
from typing import Any, Callable, Union

from nonebot.message import handle_event as nb_handle_event
from nonebot.typing import overrides

from nonebot.adapters import Bot as BaseBot

from .event import Event
from .exception import NotInteractableEventError
from .message import MessageSegment, Message


async def send(
    bot: "Bot",
    event: Event,
    message: Union[str, MessageSegment, Message],
    **params: Any,  # extra options passed to send_msg API
) -> Any:
    """默认回复消息处理函数。"""
    try:
        from_wxid: str = getattr(event, "user_id")
    except AttributeError:
        from_wxid = None
    try:
        room_wxid: str = getattr(event, "group_id")
    except AttributeError:
        room_wxid = None
    wx_id = from_wxid if not room_wxid else room_wxid
    if wx_id is None:
        raise NotInteractableEventError("Event is not interactable")

    if isinstance(message, str) or isinstance(message, MessageSegment):
        message = Message(message)

    task = []
    for segment in message:
        api = f"send_{segment.type}"
        segment.data["to_wxid"] = wx_id
        task.append(bot.call_api(api, **segment.data))

    return await asyncio.gather(*task)


class Bot(BaseBot):
    """
    wechatferry协议适配。
    """

    send_handler: Callable[["Bot", Event, Union[str, MessageSegment]], Any] = send

    async def handle_event(self, event: Event) -> None:
        await nb_handle_event(self, event)

    @overrides(BaseBot)
    async def send(
        self,
        event: Event,
        message: Union[str, MessageSegment],
        **kwargs: Any,
    ) -> Any:
        """根据 `event` 向触发事件的主体回复消息。

        参数:
            event: Event 对象
            message: 要发送的消息
            kwargs: 其他参数

        返回:
            API 调用返回数据

        异常:
            NetworkError: 网络错误
            ActionFailed: API 调用失败
        """
        return await self.__class__.send_handler(self, event, message, **kwargs)
