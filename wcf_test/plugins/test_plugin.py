from nonebot.plugin import PluginMetadata
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Message, MessageSegment # 这样的好处是可以兼容很多插件
from nonebot.params import CommandArg
from nonebot.adapters import Message as BaseMessage

__plugin_meta__ = PluginMetadata(
    name="test",
    description="测试不同返回消息的格式",
    type="application",
    usage="/test [text]",
    config=None,
    supported_adapters=None,
)

test = on_command("test", to_me())


@test.handle()
async def handle_test(message: BaseMessage = CommandArg()):
    if message.extract_plain_text() == "pic":
        # 好吧，还是准备按 onebot v11 的格式来写，这样可以使用的插件会多一些。
        await test.send(message=Message(MessageSegment.image(file="./test/data/玉兰.jpg")))
    elif message.extract_plain_text() == 'music':
        await test.send(message=Message(MessageSegment.music_custom(url="./test/data/I_love_it.mp3", audio="", title="")))
    elif message.extract_plain_text() == 'hello':
        await test.send(message=Message(MessageSegment.text("hello")))
    else:
        await test.send(message=message)

