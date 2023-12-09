from nonebot.plugin import PluginMetadata
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Message, MessageSegment  # 这样的好处是可以兼容很多插件
from nonebot.adapters.onebot.v11 import MessageEvent
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

test = on_command("test", to_me(), block=True)


@test.handle()
async def handle_test(event: MessageEvent, message: BaseMessage = CommandArg()):
    if message.extract_plain_text() == "pic":
        # 好吧，还是准备按 onebot v11 的格式来写，这样可以使用的插件会多一些。
        await test.finish(message=Message(MessageSegment.image(file="./wcf_test/data/玉兰.jpg")))
    elif message.extract_plain_text() == 'music':
        # 当前还不能发送xml卡片= =
        await test.finish(message=Message(MessageSegment.music_custom(url="不会被解析", audio="./wcf_test/data/I_love_it.mp3", title="不会被解析")))
    elif message.extract_plain_text() == 'hello':
        await test.finish(message=Message(MessageSegment.text("hello")))
    elif message.extract_plain_text() == 'link':
        await test.finish(Message(MessageSegment('link', {
            "url": "https://www.baidu.com",
            "title": "百度一下，你就知道",
            "desc": "百度两下，你就知道",
            "thumburl": "https://www.baidu.com/img/flexible/logo/pc/result.png",
            "name": "百度",
            # "account": "..."
        })))
    elif message.extract_plain_text() == 'pat':
        await test.finish(message=Message(MessageSegment('wx_pat', {'user_id': event.user_id})))
    else:
        await test.finish(message=message)
