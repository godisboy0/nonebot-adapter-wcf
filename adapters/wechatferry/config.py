from pydantic import Field, BaseModel


class Config(BaseModel):
    """ntchat 配置类"""

    debug: bool = Field(default=True)

    class Config:
        extra = "ignore"