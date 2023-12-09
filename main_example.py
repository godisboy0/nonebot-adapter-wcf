import nonebot
from adapters.wechatferry import Adapter as WechatferryAdapter
# from wcf_test.test_console_adapter import OneBotV11ConsoleAdapter as WechatferryAdapter # 本地测试用
from nonebot.drivers.none import Driver as NoneDriver

# 初始化 NoneBot
# nonebot.init(_env_file=".env")
nonebot.init(driver='~none')

# 注册适配器
driver = nonebot.get_driver()
# wechatferry 直接本地通信，不需要通信方式，所以使用 NoneDriver
assert isinstance(driver, NoneDriver)
driver.register_adapter(WechatferryAdapter)

# 在这里加载插件
nonebot.load_builtin_plugins("echo")  # 内置插件
nonebot.load_plugin("wcf_test.plugins.test_plugin")  # 第三方插件
# nonebot.load_plugins("plugins")  # 本地插件，测试用。
# nonebot.load_plugins("awesome_bot/plugins")  # 本地插件
nonebot.load_plugin("builtin_plugins.auto_help")  # 自动帮助插件

if __name__ == "__main__":
    nonebot.run()