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

    if isinstance(message, str):
        message = Message(MessageSegment.text(message))
    elif isinstance(message, MessageSegment):
        message = Message(message)

    task = []
    # 根据onebot 11 的标准，at行为是一个单独的segement，所以这里需要将at的内容拆分出来。(多个at就是多个segment)
    # 这里直接将at拼到所有的text segement 里面，然后删除at这个segement。
    # 如果没有 text segement，那就将at转化为一个单独的text segement。
    at_segs = []
    for seg in message:
        if seg.type == "at":
            at_segs.append(seg)

    if at_segs:
        text_segs: list[MessageSegment] = []
        for seg in message:
            if seg.type == "text":
                text_segs.append(seg)
        if not text_segs:
            a_msg_seg = MessageSegment.text("")
            message = Message(a_msg_seg) + message
            text_segs.append(a_msg_seg)
        
        aters = [at_seg.data['qq'] for at_seg in at_segs]
        for seg in text_segs:
            seg.data["text"] = f"{' '.join(['@'+ x for x in aters])} {seg.data['text']}"
            seg.data['aters'] = aters
        for at_seg in at_segs:
            message.remove(at_seg)

    for segment in message:
        api = f"send_{segment.type}"
        segment.data["to_wxid"] = wx_id
        task.append(bot.call_api(api, **segment.data))

    return await asyncio.gather(*task)


class Bot(BaseBot):
    """
    wechatferry协议适配。
    """

    send_handler: Callable[["Bot", Event,
                            Union[str, MessageSegment]], Any] = send

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
