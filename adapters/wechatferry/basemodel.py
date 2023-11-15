class UserInfo():
    
    def __init__(self, wx_id: str, code: str, wx_name: str, gender: str):
        self.wx_id = wx_id      # 微信id，原始id。会被作为真正的user_id 
        self.code = code        # code   微信允许改id后，新改的id的code
        self.wx_name = wx_name  # 微信昵称
        self.gender = gender    # 性别

    def __str__(self) -> str:
        return f"wx_id: {self.wx_id}, code: {self.code}, wx_name: {self.wx_name}, gender: {self.gender or ''}"