import asyncio
from typing import Any, Callable, Union
from .basemodel import UserInfo
from nonebot.message import handle_event as nb_handle_event
from nonebot.typing import overrides
from nonebot.adapters import Bot as BaseBot
from .event import Event
from .exception import NotInteractableEventError
from .message import MessageSegment, Message
import logging

logger = logging.getLogger(__name__)


async def process_msg(bot: "Bot", message: Union[str, MessageSegment, Message], room_wxid=None) -> Message:
    if isinstance(message, str):
        message = Message(MessageSegment.text(message))
    elif isinstance(message, MessageSegment):
        message = Message(message)

    # 根据onebot 11 的标准，at行为是一个单独的segement，所以这里需要将at的内容拆分出来。(多个at就是多个segment)
    # 这里直接将at拼到所有的text segement 里面，然后删除at这个segement。
    # 如果没有 text segement，那就将at转化为一个单独的text segement。
    at_segs: list[MessageSegment] = []
    for seg in message:
        if seg.type == "at":
            at_segs.append(seg)
        if seg.type == "text":
            seg.data['text'] = seg.data['text'].strip()

    if at_segs:
        text_segs: list[MessageSegment] = []
        for seg in message:
            if seg.type == "text":
                text_segs.append(seg)
        if not text_segs:
            a_msg_seg = MessageSegment.text("")
            message = a_msg_seg + message
            text_segs.append(a_msg_seg)

        aters = [at_seg.data['qq'] for at_seg in at_segs]
        at_str = " ".join([f'@{await bot.get_user_alias(x, room_wxid)}' for x in aters])
        for seg in text_segs:
            seg.data["text"] = f"{at_str} {seg.data['text']}"
            seg.data['aters'] = aters
        for at_seg in at_segs:
            message.remove(at_seg)

    return message


async def do_send_msg(bot: "Bot", wx_id: str, message: Message, **params: Any) -> Any:
    logger.info(f"【wcf】即将发送消息，{wx_id} {message} {params}")
    task = []
    for segment in message:
        api = f"send_{segment.type}"
        segment.data["to_wxid"] = wx_id
        task.append(bot.call_api(api, **segment.data))

    return await asyncio.gather(*task)


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

    message = await process_msg(bot, message, room_wxid)
    await do_send_msg(bot, wx_id, message, **params)


class Bot(BaseBot):
    """
    wechatferry协议适配。
    """

    send_handler: Callable[["Bot", Event,
                            Union[str, MessageSegment]], Any] = send

    async def send_private_msg(self, user_id: str, message: Union[str, MessageSegment, Message]):
        message: Message = await process_msg(self, message)
        await do_send_msg(self, user_id, message)

    async def send_group_msg(self, group_id: str, message: Union[str, MessageSegment, Message]):
        message: Message = await process_msg(self, message, group_id)
        await do_send_msg(self, group_id, message)

    async def handle_event(self, event: Event) -> None:
        await nb_handle_event(self, event)

    async def get_user_alias(self, user_id: str, room_id=None) -> str:
        """获取用户昵称，如果是群聊，那么会返回群昵称，如果是私聊，那么会返回用户名。找不到就返回user_id"""
        if room_id:
            return await self.call_api("get_alias_in_chatroom", group_id=room_id, user_id=user_id)
        else:
            user_info: UserInfo = await self.call_api("get_user_info", user_id=user_id)
            return user_info.wx_name if user_info else user_id

    async def get_user_info(self, user_id: str) -> UserInfo:
        """获取用户信息"""
        return await self.call_api("get_user_info", user_id=user_id)

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
