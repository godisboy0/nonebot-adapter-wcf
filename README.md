# 声明

因为极端不欢迎该项目商用，因此选用了对商用最严格的GPL协议。虽然说这也就是个君子协定而已。

但表明本人的态度是禁止该项目商用，仅用于爱好者玩票，娱乐自我、验证技术。

# 重要更新内容

## 2023-12-4

底层 wcferry 依赖版本更新到了 [v39.0.7 (2023.12.03)](v39.0.7 "2023.12.03") 可使用 `pip install --upgrade wcferry` 更新。不更新会出错。

+ 新增了下载图片能力，现在图片消息会被自动下载和发送。格式同标准的 onebot 11 image 格式
+ 新增了下载语音能力，会将语音转为mp3下载。格式同标准的 onebot11 record 格式
+ 新增了引用消息，引用消息现在会被解析，格式是自定义的格式。见[refer：引用消息](#refer：引用消息)。目前支持引用文本、引用图片、引用语音、引用另一个引用消息这几种引用消息的解析。

大幅度强化了终端测试console的能力，现在它支持一系列set命令（自行看代码找吧，就在 /wcf_test/test_console_adapter.py里面）

+ 现在可以自由切换用户身份。`:set user xxx` 将当前用户设置为xxx
+ 可以开启、进入群组模式。`:set grp` 进入群聊   `:set qgrp` 退出群聊
+ 可以显示msg_id，这是一个每次在内存中保存的，每次重开都会重新计数的消息id，可用于测试引用消息。
  发送的消息，消息id会以一条单独的消息来提示（这条消息本身也会占一个id序列）。
  接收到的消息，消息id会附在消息开头。
  `:set showid true` 开启，`:set showid false`关闭。
+ 可以模拟发送image、video、voice、refer消息。
  + `image:/path/to/pic`     发送图片消息，发出一个标准的 onebot 11 image 消息
  + `video:/path/to/video` 发送视频消息，发出一个标准的 onebot 11 video 消息
  + `voice:/path/to/mp3`     发送语音消息，发出一个标准的 onebot 11 record 消息
  + `refer:[msgid] text`     发送引用消息，发出一个自定的 [refer：引用消息](#refer：引用消息) 格式消息。

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
   ~ pip install nonebot-adapter-console  # 终端测试需要
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

# 自定义扩展

## refer：引用消息

引用消息的消息段（MessageSegment）的type统一为：`wx_refer`，data是一个json，json格式分别如下；

1. 引用文本消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refer": {
       "id": refer_msg_id,
       "type": "text",
       "speaker_id": "user_id",   // 被引用消息的用户id
       "content": "被引用消息的文本"
     }
   }
   ```

2. 引用图片消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refer": {
       "id": refer_msg_id,
       "type": "image",
       "speaker_id": "user_id",   // 被引用消息的用户id
       "content": "被引用图片的path"
     }
   }
   ```

3. 引用语音消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refer": {
       "id": refer_msg_id,
       "type": "voice",
       "speaker_id": "user_id",   // 被引用消息的用户id
       "content": "被引用mp3文件的path"
     }
   }
   ```

4. 引用引用消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refer": {
       "id": refer_msg_id,
       "type": "refer",
       "speaker_id": "user_id",   // 被引用消息的用户id
       "content": "被引用消息的文本" // 只可能是文字
     }
   }
   ```

## revoke：撤回消息

撤回消息的消息段的type为`revoke`，data格式为：

```json
{
  "revoke_msg_id": revoked_msg_id
}
```

## bot方法扩展

啊懒得写了，自己看bot.py里面的方法吧= =
