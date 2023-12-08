"""
用于转换消息
"""
from typing import Dict, Callable, TypeVar
from .message import MessageSegment, Message
from .sqldb import database
from wcferry import Wcf, WxMsg
from .type import WxType, WXSubType
from .utils import logger


MSG_CONV = TypeVar("MSG_CONV", bound=Callable[[WxMsg, str, Wcf, database], Message])

# TODO 返回值在考虑下
SUB_CONV = TypeVar("SUB_CONV", bound=Callable[[WxMsg, str, Wcf, database], MessageSegment])

msg_conv_dict: dict[WxType, MSG_CONV] = {}

sub_msg_conv_dict: dict[WXSubType, MSG_CONV] = {}

def msg_converter(wxtype: WxType, desc: str):
    logger.info(f"Registering multi_msg_handler: {wxtype} {desc}")
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in multi_msg_handler: {e}")
                return None
        msg_conv_dict[wxtype] = wrapper
        return wrapper
    return decorator

