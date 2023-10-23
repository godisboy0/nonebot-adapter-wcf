# 声明

因为极端不欢迎该项目商用，因此选用了对商用最严格的GPL协议。虽然说这也就是个君子协定而已。

但表明本人的态度是禁止该项目商用，仅用于爱好者玩票，娱乐自我、验证技术。

# 致谢

感谢 [wechatferry](https://github.com/lich0821/WeChatFerry) 项目和 [nonebot2](https://github.com/nonebot) 项目，[adapter-ntchat](https://github.com/JustUndertaker/adapter-ntchat)，以及[nonebot2-onebot-adapter](https://github.com/nonebot/adapter-onebot) 项目。

wechatferry 项目带我入了机器人的坑，之后我自己开发了一个简单的机器人开发框架，虽然基本功能都具备，也做到了 IM 平台无关，但精力逐渐难以跟上继续维护，很多设想的功能无法及时添加进去，而且我越来越想专注于 **功能** 的开发，对框架的开发逐渐失去了兴趣。这时候看到nonebot2，就想做个adapter，把 wechatferry 项目和 nonebot2 的能力整合起来。

不过nonebot2的adapter开发者指南过于抽象😭，以至于我根本看不明白，于是开始翻看 [nonebot2 adapter store](https://nonebot.dev/store/adapters) 中唯一一个 wechat adapter，学习里面的流程。在这个过程中，抄袭了大量该开发者的代码，同时发现绝大多数 nonebot2 的插件，即我通常所说的 **功能** 性机器人，都基于 onebot.v11 的 message 和 messageSegment，如果完全自定义自己的 adapter，则可能与绝大多数 插件 存在适配问题，因此，我打算先以 onebot.v11 的 message 和 messageSegment 为基础message进行开发，先实现基础的收发信息功能，之后再在此基础上开发可以使用 wechat 平台独有能力的  message 和 messageSegment ，以尽量保证兼容性。

折腾了两天，终于做到了正常接收文本信息，发送文本、音乐、视频、文件信息，在此公布出来。之后会随缘更新，比如看到哪个插件很好想白嫖发现现有功能不支持，会继续扩展能力。

# 安装

必须是一台windows电脑，并安装了特定版本的wechat，具体版本请看本节最后。

1. 首先安装 nonebot2 项目

   ```shell
   ~ conda create --name webot python=3.10
   ~ conda activate webot
   ~ python -m pip install --user pipx
   ~ python -m pipx ensurepath
   # 可能需要重启 shell 才可用。
   ~ pipx install nb-cli
   ```
2. 安装 nonebot2-onebot-adapter

   ```shell
   ~ nb adapter install nonebot-adapter-onebot
   ```
3. 安装wechatferry

   ```shell
   ~ pip install --upgrade wcferry
   ```
4. 下载当前项目

   ```shell
   ~ git clone git@github.com:godisboy0/nonebot-adapter-wcf.git
   ```

之后，主目录下的 main_example.py 就是主入口，可以按需修改后运行。注意，wechat的版本需要和wechatferry要求的版本一致，具体可以参照：[wechatferry的文档](https://github.com/lich0821/WeChatFerry)

不过建议复制出来一个main.py，在这个基础上做修改。这样不受git的管控哈~另外，plugins的开发我放到另外一个暂时私密的repo去了，以后或许会开放出来吧！
