# 声明

因为极端不欢迎该项目商用，因此选用了对商用最严格的GPL协议。虽然说这也就是个君子协定而已。

但表明本人的态度是禁止该项目商用，仅用于爱好者玩票，娱乐自我、验证技术。

# 重要更新内容

## 2023-12-10

1. 底层 wcferry 依赖版本更新到了 [v39.0.10 (2023.12.08)](https://github.com/lich0821/WeChatFerry#v39010-20231208) 可使用 `pip install --upgrade wcferry` 更新。不更新会出错。
2. 新增了拍一拍能力，直接发送[拍一拍消息](#拍一拍)即可。
3. 新增了发送链接能力，直接发送[链接消息](#链接消息)即可。
4. 新增了一个根据 nonebot 的\_\__plugin\_meta\_\_字段来自动生成帮助消息的通用插件，这下就不用费心写插件的帮助消息了。

## 2023-12-8

1. 新增了更加丰富的引用消息格式。

2. 新增了[文件消息](#文件消息)。（自定义扩展）

3. 新增了链接信息。是标准的 [onebot链接分享segment](https://github.com/botuniverse/onebot-11/blob/master/message/segment.md#%E9%93%BE%E6%8E%A5%E5%88%86%E4%BA%AB)

4. 新增了聊天记录的消息格式。见[聊天记录](#聊天记录消息)

   + 已知问题：

     除非聊天记录里的图片、视频、文件消息是机器人所在群聊里的，否则无法提取里面的视频、图片和文件。也就是说，假如你直接从其他群转发一个聊天记录给机器人，机器人不在聊天记录的那个原始群里面，就提取不了聊天记录里的图片、视频、文件。
     
     对应的表现是，图片、视频、文件的`MessageSegment`中的`file`字段为`None`
     
     （主要是wcferry目前必须要msg_id才能下载文件，不能直接利用消息中的cdn数据。而转发的聊天记录里提取不出来msg id，期待某一天wcferry项目支持）
     
   + 有可能丢失聊天记录里的消息。

     就是比如聊天记录里有20条消息，我转完之后，进入系统里的只有12条。因为微信不同版本会新增一些消息类型，没有支持，或者处理过程中出现了异常，于是某一条消息就被丢弃了。

5. test_console 支持模拟发送文件和链接信息，具体格式如下：

   + `file:/path/to/file` 模拟发送文件。
   + `link:title#desc#url#img_path`模拟发送一个链接。

6. 从`wcferry.WxMsg`到`onebot11 Message`的消息转化代码，现在全部挪到了`msg_converters.py`中，这样看起来更清晰，支持新的类型也更加方便。有任何发现文档中的消息格式与实际有出入的，请直接看这个文件中的各种消息格式。

7. 新增了一个debug_helper类。其实主要是用于框架开发过程，可以直接把一些很长的字符串或者当前msg直接以文件形式发送给root_user，在那种本地开发、云端部署debug的场景下非常有用。

   可以在vscode的debug console里直接import进来，随处使用。

8. 在config.py中新增了一个配置项：`echo_root_msg`，为`true`时，会将root_user发送给bot的所有msg直接以文件形式回传，包括`wcferry/WxMsg`的所有字段。和4的效果一样，就是为了开发框架时debug方便。

## 2023-12-4

底层 wcferry 依赖版本更新到了 [v39.0.7 (2023.12.03)](https://github.com/lich0821/WeChatFerry#v3907-20231203) 可使用 `pip install --upgrade wcferry` 更新。不更新会出错。

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

不过nonebot2的adapter开发者指南过于抽象😭，以至于我根本看不明白，于是开始翻看 [nonebot2 adapter store](https://nonebot.dev/store/adapters) 中唯一一个 wechat adapter，学习里面的流程。在这个过程中，抄袭了大量该开发者的代码（其实现在改来改去已经和原代码没多大关系了，但是仍然特别感谢他给的提示），同时发现绝大多数 nonebot2 的插件，即我通常所说的 **功能** 性机器人，都基于 onebot.v11 的 message 和 messageSegment，如果完全自定义自己的 adapter，则可能与绝大多数 插件 存在适配问题，因此，我打算先以 onebot.v11 的 message 和 messageSegment 为基础message进行开发，先实现基础的收发信息功能，之后再在此基础上开发可以使用 wechat 平台独有能力的  message 和 messageSegment ，以尽量保证兼容性。

建议先阅读[onebot11官方segement类型文档](https://github.com/botuniverse/onebot-11/blob/master/message/segment.md)熟悉一下有哪些官方支持的类型。然后再看一下这个文档下面的一些扩展类型。

折腾了两天，终于做到了正常接收文本信息，发送文本、音乐、视频、文件信息，在此公布出来。之后会随缘更新，比如看到哪个插件很好想白嫖发现现有功能不支持，会继续扩展能力。

大部分[nonebot商店](https://nonebot.dev/store/plugins)中的插件（除了音乐类，因为音乐类一般框架都发id，而不是文件，但wcferry当前还不支持发送xml），都可以直接拿过来稍微修改或者根本不改直接使用。

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
   # 可能还有不少依赖需要装，总之运行时缺啥装啥吧。。
   ```
4. 下载当前项目

   ```shell
   ~ git clone git@github.com:godisboy0/nonebot-adapter-wcf.git
   ```

之后，主目录下的 main_example.py 就是主入口，可以按需修改后运行。注意，wechat的版本需要和wechatferry要求的版本一致，具体可以参照：[wechatferry的文档](https://github.com/lich0821/WeChatFerry)

不过建议复制出来一个`main.py`，在这个基础上做修改。这样不受git的管控哈~另外，plugins的开发我放到另外一个暂时私密的repo去了，~~以后或许会开放出来吧！~~(有不少key图省事直接写到了plugins里，不会公开了)

# 自定义扩展

## 文件消息

文件消息的消息段（MessageSegment）的type为：`file`，data格式如下：

```json
{
  "file": "/path/to/file",
  "name": "文件名"
}
```

在代码中这么创建的：

```python
from nonebot.adapters.onebot.v11 import Message, MessageSegment

file_msg = Message(MessageSegment('file', {'file': file_path, "name": file_name}))
```

## refer：引用消息

引用消息的消息段（MessageSegment）的type统一为：`wx_refer`，data是一个json，json格式如下，这个json的格式和聊天记录的格式保持一致。

在代码中这么创建的：

```python
from nonebot.adapters.onebot.v11 import Message, MessageSegment

refer_msg = Message(MessageSegment("wx_refer", {
  "content": "引用消息的文本，就是你引用那条消息后输入的内容",
  "refered": {
    "id": 798129797979,     # 被引用的消息的id
    "time": 1212121212,		  # 一个时间戳，是被引用消息的发送时间戳，以秒为单位
    "sender": "user_id",    # 被引用消息的发送者id
    "sender_name": "god",		# 被引用消息的发送者昵称，可能为None或者空字符串。
    "msg": Message(xxx)			# 一个标准的 Message 信息，请自行解析其中 MessageSegment 的 type 来区分是干嘛的。
  }
}))
```

1. 引用文本消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refered": {
       "id": 798129797979,
       "time": 10289701972,
       "sender": "user_id",    
       "sender_name": "god",			
       "msg": Message(MessageSegment.text(refered_content))			# 就是文本消息
     }
   }
   ```

2. 引用图片消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refered": {
       "id": 798129797979,
       "time": 10289701972,
       "sender": "user_id",    
       "sender_name": "god",			
       "msg": Message(MessageSegment.image(pic_path))						# 图片路径
     }
   }
   ```

3. 引用语音消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refered": {
       "id": 798129797979,
       "time": 10289701972,
       "sender": "user_id",    
       "sender_name": "god",			
       "msg": Message(MessageSegment.record(mp3_path))
     }
   }
   ```

4. 引用引用消息

   ```json
   {
     "content": "引用消息的文本，就是你引用那条消息后输入的内容",
     "refered": {
       "id": 798129797979,
       "time": 10289701972,
       "sender": "user_id",    
       "sender_name": "god",			
       "msg": Message(MessageSegment("wx_refer", {"content": content})  # 只保留了一个文本信息。
     }
   }
   ```

5. 引用video消息、文件消息等。

   总之就是标准的video和文件消息格式啦~

## revoke：撤回消息

撤回消息的消息段的type为`revoke`，data格式为：

```json
{
  "revoke_msg_id": revoked_msg_id
}
```

## 聊天记录消息

就是转发过来的群聊、私聊记录。

消息段（MessageSegment）的type统一为：`wx_multi`，格式非常简单，只有一个msg_list字段。msg_list中的每一个元素，和引用的每一个元素的消息格式完全一致。

在代码中这么创建一条聊天记录消息。

```python
from nonebot.adapters.onebot.v11 import Message, MessageSegment

multi_msg = Message(MessageSegment('wx_multi', {'msg_list': msg_list}))
```

下面是一个示例，并没有穷举所有可能。

```json
{
  "msg_list": [
    {
        "id": 1234567,							// 原始消息id，可能为None。
        "time": 1207203870,					// 一个以秒为单位的时间戳
        "sender": "god",						// 发送人wx_id，可能为None（新版微信增强了对隐私的保护，直接取消了这个字段）
        "sender_name": "发送者昵称",	 // 发送者昵称，基本不会为None
        "msg": Message(MessageSegment.image(pic_path)) // 图片消息
    },
    {
        "id": 1234567,							
        "time": 1207203870,					
        "sender": "god",						
        "sender_name": "发送者昵称",	 
        "msg": Message(MessageSegment.share(link, title, None, None)) // 链接消息解析图片和内容很麻烦，直接为None。
    },
    {
        "id": 1234567,							
        "time": 1207203870,					
        "sender": "god",						
        "sender_name": "发送者昵称",	 
        "msg": Message(MessageSegment.video(video_path)) // 视频消息
    }
  ]
}
```

文本消息、文件消息、引用消息。都是一样的。

## 拍一拍

```json
{
  "type": "wx_pat",
  "data": {
    "user_id": "user_id"	// 要拍的人，私聊也要传。
  }
}
```

## 链接消息

之所以不用onebot官方的share，是因为缺少几个字段。当然onebot标准的share消息也能处理。

```json
{
  "type": "link",
  "data": {
      "url": "https://www.baidu.com",
      "title": "百度一下，你就知道",
      "desc": "百度两下，你就知道",
      "thumburl": "https://www.baidu.com/img/flexible/logo/pc/result.png",
      "name": "百度",
      "account": "gh-"		// 公众号的id，可以带小头像
  }
}
```

## bot方法扩展

啊懒得写了，自己看bot.py里面的方法吧= =就是单独扩展了一个获取用户昵称、发送私聊、群聊消息这三个接口。
