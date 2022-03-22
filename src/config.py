import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DEBUG: bool = os.getenv("DEBUG", True)
    VERSION: str = "0.1-alpha"
    BASE_URL: str = "https://www.cotps.com:8443"
    LOGIN_TYPE: str = "mobile"
    LOGIN_URL: str = "/api/mine/sso/user_login_check"
    BALANCE_URL: str = "/api/mine/user/getDealInfo"
    ORDER_CREATE_URL: str = "/api/mine/user/createOrder"
    ORDER_SUBMIT_URL: str = "/api/mine/user/submitOrder"


settings = Settings()