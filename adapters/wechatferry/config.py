from pydantic import Field, BaseModel


class AdapterConfig(BaseModel):
    """wechatferry 配置类"""

    debug: bool = Field(default=True)
    """是否开启调试模式"""
    db_path: str = Field(default="./data")  
    """数据库路径，默认为当前运行路径下的 data 文件夹，该文件夹已经被 .gitignore 忽略"""
    

    class Config:
        extra = "ignore"