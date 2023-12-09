"""
这是一个自动帮助插件，会统计你现有的插件，并且自动生成帮助信息。需要插件有合理的 _plugin_meta_ 属性。
1. 如果meta属性中的 __plugin_meta__.extra.help_info 为一个下面格式的list，将直接使用这个list作为帮助信息。
{
    "name": "插件名",
    "desc": "插件描述",
    "cmds": ["命令", "alias1", "alias2"],
    "sub_cmds": [
        ("命令1", "命令1效果"), ("命令2", "命令2效果")
    ],
    "auth_method": async Callable[(user_id, room_id) -> bool]
}
具体字段说明如下：
name: 插件名，不填会用 __plugin_meta__.name 代替；
desc: 插件描述，不填会用 __plugin_meta__.description 代替；
cmds: 触发命令，可以有多个alias；

sub_cmds: 子命令，可以有多个，格式为 (命令, 命令效果)，示例如下：
[("/drawer help", "查看帮助"), ("/drawer 参考", "随机获取一个参考图"), ("/drawer config", "查看或修改配置信息")]
子命令不会直接暴露，需要help + 插件名查看，如：/help drawer

auth_method：可选，一个判断用户是否有权限使用的方法。如果有这个字段，则会在每次调用时调用这个方法，判断用户是否能使用这个插件。
如果 auth_method 不为空且返回 False，则不会将这个插件暴露在帮助信息中。
可以直接是一个方法，那会被直接调用，也可以是方法名字符串，只要参数对就行。
注意方法需要是异步方法，且参数为 user_id, room_id，返回值为 bool。

注意：help_info 是一个list，因为有很多插件有多个命令，所以这里使用list。

2. 如果 __plugin_meta__.extra.disable_help 为 True，则不会将这个插件暴露在帮助信息中。

3. 如果没有help_info，则默认使用插件的name、description、usage, homepage作为帮助信息，当查看具体插件帮助时，会提示没有详细信息。

4. 如果连 __plugin_meta__ 都没有，则不会暴露在帮助信息中。
"""

from typing import List
from nonebot.rule import to_me
from nonebot import on_command
from nonebot import get_loaded_plugins
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent
from types import ModuleType
from adapters.wechatferry.utils import logger
from nonebot.typing import T_State
from .config import HelperConfig
from nonebot import get_driver

help_bot = on_command("help", rule=to_me(), aliases={
                      '帮助', "菜单"}, priority=180, block=True)


config: HelperConfig = HelperConfig.parse_obj(get_driver().config)

@help_bot.handle()
async def handle_help(event: MessageEvent, state: T_State):
    mod_list = [elm.module for elm in get_loaded_plugins()]
    msg_list: list[str] = []
    for mod in mod_list:
        if mod.__name__ in config.not_showed_plugin_names:
            continue
        if hasattr(mod, "__plugin_meta__"):
            msg: list[str] = await build_from_meta(event, mod, mod.__plugin_meta__)
            if msg:
                msg_list.extend(msg)

    await help_bot.finish("\n".join(msg_list))


async def build_from_meta(event: MessageEvent, mod: ModuleType, meta: PluginMetadata) -> list[str]:
    if meta.extra.get("disable_help", False):
        return ""
    elif "help_info" in meta.extra:
        return await build_from_help_info(event, mod, meta, meta.extra["help_info"])
    else:
        return [await build_from_usage(meta.name, meta.description, meta.usage, meta.homepage)]


async def build_from_help_info(event: MessageEvent, mod: ModuleType, meta: PluginMetadata, help_info: List[dict]) -> list[str]:
    msg_list = []
    for info in help_info:
        authed = await check_auth(event, mod, info)
        if authed:
            name = info.get("name", meta.name)
            desc = info.get("desc", meta.description)
            cmds = info.get("cmds", [])
            if not name and not desc and not cmds:
                continue
            msg_list.append(f"{name or '未知'}: {desc or '未知功能'}\n命令：{cmds or '未知'}\n")
    return msg_list


async def build_from_usage(name: str, desc: str, usage: str, homepage: str) -> str:
    msg = f"{name or '未知'}: {desc or '未知功能'}\n用法：{usage or '未知'}\n"
    if homepage:
        msg += f"主页：{homepage}\n"
    return msg


async def check_auth(event: MessageEvent, mod: ModuleType, info: dict) -> bool:
    try:
        if "auth_method" in info:
            auth_method = info["auth_method"]
            if isinstance(auth_method, str):
                auth_method = getattr(mod, auth_method)
            return await auth_method(event.user_id, event.group_id if isinstance(event, GroupMessageEvent) else None)
        else:
            return True
    except Exception as e:
        logger.error(f"check auth failed: {e}, default to True")
        return True
