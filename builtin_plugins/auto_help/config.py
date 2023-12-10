from pydantic import BaseModel, Field


class HelperConfig(BaseModel):

    not_showed_plugin_names = Field(
        [
            'auto_help',
            'nonebot_plugin_apscheduler',
            'wcf_test.plugins.test_plugin',
            'nonebot.plugins.echo'
        ],
        description="不显示的插件名, 应该是全限定名，如 `awesome_bot.plugins.test_plugin`"
    )
