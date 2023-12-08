from pydantic import Field, BaseModel


class AdapterConfig(BaseModel):
    """wechatferry 配置类"""

    debug: bool = Field(default=True)
    """是否开启调试模式"""
    db_path: str = Field(default="./data")  
    """数据库路径，默认为当前运行路径下的 data 文件夹，该文件夹已经被 .gitignore 忽略"""
    echo_root_msg: bool = Field(default=False)
    """是否将 root_user 的信息直接做成json回传给root_user"""
    """在debug时非常有用，特别是你的开发机器和部署微信的机器不是同一台时。用过的都说好"""
    

    class Config:
        extra = "ignore"