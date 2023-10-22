from typing import Any, Dict, Optional

from nonebot.exception import ActionFailed
from nonebot.utils import logger_wrapper


class Logger:
    def __init__(self) -> None:
        self.log = logger_wrapper("wechatferry")

    def info(self, msg: str, e: Exception=None) -> None:
        self.log("INFO", msg, e)
    
    def error(self, msg: str, e: Exception=None) -> None:
        self.log("ERROR", msg, e)

    def debug(self, msg: str, e: Exception=None) -> None:
        self.log("DEBUG", msg, e)
    
    def warning(self, msg: str, e: Exception=None) -> None:
        self.log("WARNING", msg, e)

logger = Logger()

def handle_api_result(result: Optional[Dict[str, Any]]) -> Any:
    """处理 API 请求返回值。

    参数:
        result: API 返回数据

    返回:
        API 调用返回数据

    异常:
        ActionFailed: API 调用失败
    """
    if isinstance(result, dict):
        if result.get("status") == "failed":
            raise ActionFailed(**result)
        return result.get("data")
