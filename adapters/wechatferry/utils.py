from typing import Any, Dict, Optional

from nonebot.exception import ActionFailed
from nonebot.utils import logger_wrapper
from nonebot.utils import escape_tag
import os
import requests
import re
import asyncio

class Logger:
    def __init__(self) -> None:
        self.log = logger_wrapper("wechatferry")

    def info(self, msg: str, e: Exception=None) -> None:
        self.log("INFO", escape_tag(str(msg)), e)
    
    def error(self, msg: str, e: Exception=None) -> None:
        self.log("ERROR", escape_tag(str(msg)), e)

    def debug(self, msg: str, e: Exception=None) -> None:
        self.log("DEBUG", escape_tag(str(msg)), e)
    
    def warning(self, msg: str, e: Exception=None) -> None:
        self.log("WARNING", escape_tag(str(msg)), e)

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


class downloader:
    def __init__(self, url, file_name, path: str, override: bool = True, chunk_size: int = 1024, headers={}) -> None:
        rstr = r"[ \/\\\:\*\?\"\<\>\|\&]"  # '/ \ : * ? " < > |'
        file_name = re.sub(rstr, "_", file_name)
        url = str(url).strip('"')
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        self.__url = url
        self.__path = path
        self.__file_name = file_name
        self.__override = override
        self.__chunk_size = chunk_size
        self.headers = headers if headers else {}

    async def downloadAsync(self) -> str:
        return await asyncio.get_event_loop().run_in_executor(None, self.download)

    def download(self) -> str:
        if not self.__url or self.__url.lower == 'none':
            return None
        final_path = os.path.join(self.__path, self.__file_name)
        if self.__override:
            if os.path.exists(final_path):
                os.remove(final_path)
        else:
            if os.path.exists(final_path):
                return final_path
        try:
            response = requests.get(self.__url, stream=True,
                                    timeout=3, headers=self.headers)
            size = 0
            if response.status_code == 200:
                try:
                    with open(final_path, 'wb') as file:
                        for data in response.iter_content(chunk_size=self.__chunk_size):
                            file.write(data)
                            size += len(data)
                    return final_path
                except Exception:
                    logger.warning(
                        f'链接{self.__url}下载失败，状态码：{response.status_code}, file_name: {self.__file_name}')
                    return None
            else:
                logger.warning(
                    f'链接{self.__url}下载失败，状态码：{response.status_code}, file_name: {self.__file_name}')
                return None
        except Exception as e:
            logger.error(f'链接{self.__url}下载失败', e)
            return None