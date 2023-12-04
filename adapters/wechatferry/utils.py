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


def file_md5(file_path) -> Optional[str]:
    """计算文件的 MD5 值。

    参数:
        file_path: 文件路径

    返回:
        文件的 MD5 值
    """
    import hashlib

    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return hashlib.md5(data).hexdigest()
    except Exception as e:
        logger.error(f"计算文件 {file_path} 的 MD5 值失败: {e}")
        return None
