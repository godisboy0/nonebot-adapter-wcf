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
import re

help_bot = on_command("help", rule=to_me(), aliases={
                      '帮助', "菜单"}, priority=180, block=True)


config: HelperConfig = HelperConfig.parse_obj(get_driver().config)

weizhi_index = 0


class PluginInfo:
    def __init__(self, name: str, help_info: str, sub_cmds: dict[str, str], auth_method: callable):
        self.name = name
        self.help_info = help_info
        self.sub_cmds = sub_cmds
        self.auth_method = auth_method

    def __str__(self) -> str:
        return f"{self.name}: {self.help_info}\n子命令：{self.sub_cmds}"

    def __repr__(self) -> str:
        return str(self)


plugin_info_dict: dict[str, PluginInfo] = None


@help_bot.handle()
async def handle_help(event: MessageEvent, state: T_State):
    mod_list = [elm.module for elm in get_loaded_plugins()]
    msg_list: list[str] = []
    global plugin_info_dict
    if plugin_info_dict is None:
        await build_plugin_info_dict(mod_list)

    input_cmd = re.sub(r"^/(help|帮助|菜单)", "", event.get_plaintext()).strip()
    if not input_cmd:
        # /help
        for info in plugin_info_dict.values():
            authed = await check_auth(event, info.auth_method)
            if authed:
                msg_list.append(info)
        if not msg_list:
            await help_bot.finish("这里是一片荒漠，除了孤独什么也没有！")
        state["msg_list"] = msg_list
    elif input_cmd in plugin_info_dict:
        # /help drawer
        await help_sub_cmd(event, input_cmd)
    else:
        await help_bot.finish(f"米有找到 {input_cmd} 呢，试试 /help 再看看吧！")


@help_bot.handle()
async def send_help(event: MessageEvent, state: T_State):
    msg_list = state["msg_list"]
    # 3条一组，接受翻页。
    cmd = event.get_plaintext().strip()
    if state.get('page') is None:
        state['page'] = 1
    state['total_page'] = len(msg_list) // 3  + (1 if len(msg_list) % 3 != 0 else 0)

    if cmd == "n":
        if state['page'] + 1 <= state['total_page']:
            state['page'] += 1
        else:
            await help_bot.reject("已经是最后一页了！")
    elif cmd == "p":
        if state['page'] > 1:
            state['page'] -= 1
        else:
            await help_bot.reject("已经是第一页了！")
    elif cmd.isdigit():
        index = int(cmd)
        if index > 0 and index <= len(msg_list):
            await help_sub_cmd(event, msg_list[index - 1].name)
        else:
            await help_bot.reject("哎呀，数字太大了，我接受不了！")
    elif cmd == "q":
        await help_bot.finish("再见！")

    start_index = state['page'] * 3 - 3
    end_index = start_index + 3
    msg = "\n".join(
        f"{i+start_index+1}. {item.help_info}" for i, item in enumerate(msg_list[start_index:end_index])
    )

    if state['total_page'] != 1:
        msg += f"\n第{state['page']}/{state['total_page']}页 p,n翻页,q退出,序号看详情"
    await help_bot.reject(msg)


async def help_sub_cmd(event: MessageEvent, input_cmd: str):
    info = plugin_info_dict[input_cmd]
    authed = await check_auth(event, info.auth_method)
    if not authed:
        await help_bot.finish(f"米有找到 {input_cmd} 呢，试试 /help 再看看吧！")
    if not info.sub_cmds:
        await help_bot.finish(f"{info.name} 没有子命令哦！")
    else:
        await help_bot.finish(
            f"{info.name} 的子命令有：\n" + "\n".join([f"{x}：{y}" for x, y in info.sub_cmds.items()]))


async def build_plugin_info_dict(mod_list: list[ModuleType]):
    global plugin_info_dict
    plugin_info_dict = {}
    for mod in mod_list:
        if mod.__name__ in config.not_showed_plugin_names:
            continue
        if hasattr(mod, "__plugin_meta__"):
            meta = mod.__plugin_meta__
            if meta.extra.get("disable_help", False):
                continue
            elif "help_info" in meta.extra:
                await build_plugin_info_from_help_info(mod, meta, meta.extra["help_info"])
            else:
                await build_plugin_info_from_usage(mod, meta)


async def build_plugin_info_from_help_info(mod: ModuleType, meta: PluginMetadata, help_info: List[dict]):
    for info in help_info:
        auth_method = info.get("auth_method")
        if isinstance(auth_method, str) and hasattr(mod, auth_method):
            auth_method = getattr(mod, auth_method)

        auth_method = auth_method or __auth_pass_method

        global weizhi_index
        weizhi_index += 1
        name = info.get("name", meta.name) or ("未知" + str(weizhi_index))
        desc = info.get("desc", meta.description)
        cmds = info.get("cmds", [])
        if not name and not desc and not cmds:
            continue
        sub_cmds = {x: y for x, y in info.get("sub_cmds", [])}

        plugin_info_dict[name] = PluginInfo(
            name,
            f"{name or '未知'}{'：'+ desc if desc else ''}\n命令：{' '.join(cmds) or '未知'}",
            sub_cmds,
            auth_method
        )


async def __auth_pass_method(user_id: int, room_id: int):
    return True


async def build_plugin_info_from_usage(mod: ModuleType, meta: PluginMetadata):
    global weizhi_index
    weizhi_index += 1
    name = meta.name or ("未知" + str(weizhi_index))
    plugin_info_dict[name] = PluginInfo(
        name,
        f"{meta.name or '未知'}{'：'+ meta.description if meta.description else ''}\n命令：{meta.usage or '未知'}",
        {},
        __auth_pass_method
    )


async def build_from_meta(event: MessageEvent, mod: ModuleType, meta: PluginMetadata) -> list[str]:
    if meta.extra.get("disable_help", False):
        return ""
    elif "help_info" in meta.extra:
        return await build_from_help_info(event, mod, meta, meta.extra["help_info"])
    else:
        return [await build_from_usage(meta.name, meta.description, meta.usage)]


async def build_from_help_info(event: MessageEvent, mod: ModuleType, meta: PluginMetadata, help_info: List[dict]) -> list[str]:
    msg_list = []
    for info in help_info:
        authed = await check_auth(event, mod, info)
        if authed:
            name = info.get("name", meta.name) or "未知"
            desc = info.get("desc", meta.description)
            cmds = info.get("cmds", [])
            if not name and not desc and not cmds:
                continue
            msg_list.append(
                f"{name or '未知'}{'：'+ desc if desc else ''}\n命令：{' '.join(cmds) or '未知'}\n")
    return msg_list


async def build_from_usage(name: str, desc: str, usage: str) -> dict[str, str]:
    msg = f"{name or '未知'}: {desc or '未知功能'}\n用法：{usage or '未知'}\n"
    return msg


async def check_auth(event: MessageEvent, auth_method: callable) -> bool:
    try:
        return await auth_method(event.user_id, event.group_id if isinstance(event, GroupMessageEvent) else None)
    except Exception as e:
        logger.error(f"check auth failed: {e}, default to True")
        return True
