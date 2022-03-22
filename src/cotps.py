import requests
from base64 import b64decode
from pathlib import Path
from json.decoder import JSONDecodeError
from typing import Union, Optional, Dict, Any
from urllib.parse import urljoin

from spec_utils._base import OAuthClient
from spec_utils._schemas import JWT

from .config import settings
from .utils import Decorators


class Client(OAuthClient):
    __name__ = "COTPS"

    def __init__(
        self,
        *,
        username: str,
        pwd: str,
        login_type: str = settings.LOGIN_TYPE,
        url: Union[str, Path] = settings.BASE_URL,
        session: Optional[requests.Session] = None
    ) -> None:
        super().__init__(
            url=url,
            username=username,
            pwd=pwd,
            session=session
        )

        self.headers = {}

        ### None values
        self.token = None
        self.cookie = None


        # login type
        self.login_type = login_type

    def refresh_headers(
        self,
        token: Optional[Dict[str, Any]] = None,
        remove_token: Optional[bool] = False,
        remove_content_type: Optional[bool] = False,
        cookie: Optional[str] = None
    ) -> None:
        """ Refresh client headers for requests structure

        Args:
            token (Optional[Dict[str, Any]], optional):
                JSONResponse from 'Auth/login/' t3 api.
                Defaults to None.
            remove_token (Optional[bool], optional):
                Boolean to remove token from client.
                Defaults to False.
            remove_content_type (Optional[bool], optional):
                Boolean to remove content type for form encoded requests.
                Defaults to False.
        """
        
        if remove_token:
            # tooken
            self.token = None
            self.headers.pop("authorization", None)
            self.session.headers.pop("authorization", None)
            
            # cookie
            self.cookie = None
            self.headers.pop("Cookie", None)
            self.session.headers.pop("Cookie", None)

        if remove_content_type:
            self.headers.pop("Content-Type", None)
            self.session.headers.pop("Content-Type", None)

        if token:
            self.token = JWT(
                access_token=token.get('token', ''),
                token_type='Bearer'
            )
        
        if self.token:
            self.headers.update({
                "authorization": '{} {}'.format(
                    self.token.token_type,
                    self.token.access_token
                )
            })

        if "Content-Type" not in self.headers and not remove_content_type:
            self.headers.update({
                "Content-Type": "application/json;charset=UTF-8"
            })

        if cookie:
            self.cookie = cookie

        if cookie and not remove_token:
            self.headers.update({
                "Cookie": cookie
            })


    @property
    def is_connected(self):
        """ Informs if client has headers and access_token. """
        return bool("authorization" in self.headers and self.token != None)


    def post(
        self,
        url: Optional[Union[str, Path]] = None,
        path: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        get_headers: Optional[bool] = None,
        **kwargs
    ):
        # prepare url
        url = url or urljoin(self.client_url.geturl(), path)

        # consulting visma
        response = self.session.post(
            url=url,
            params=params,
            data=data,
            json=json,
            **kwargs
        )

        if get_headers:
            return response.headers

        # if session was closed, reconect client and try again
        if response.status_code == 401 and self.session_expired:
            self.relogin()
            return self.post(
                path=path,
                params=params,
                data=data,
                json=json,
                **kwargs
            )

        # raise if was an error
        if response.status_code not in range(200, 300):
            raise ConnectionError({
                "status": response.status_code,
                "detail": response.text
            })

        try:
            return response.json()
        except JSONDecodeError:
            return response.text

    
    def login(self) -> None: 
        
        if self.is_connected:
            return

        self.refresh_headers(remove_token=True)

        credentials = {
            "mobile": self.username,
            "password": b64decode(self.pwd).decode('utf-8'),
            "type": self.login_type
        }

        # consulting nettime
        json_data = self.post(
            path='/api/mine/sso/user_login_check',
            data=credentials,
            get_headers=True
        )

        # update access token and headers
        self.refresh_headers(
            token={"token": json_data.get('authorization', '')},
            cookie=json_data.get('Set-Cookie', '')
        )

        # refresh session with updated headers
        self.refresh_session()


    def logout(self) -> None:
        """ Send a token to blacklist in backend. """

        if not self.is_connected:
            return

        # clean token and headers for safety
        self.refresh_headers(remove_token=True)
        self.refresh_session()


    def relogin(self) -> None:
        """ Reconnect client cleaning headers and access_token. """

        # logout and login. Will fail if has no token
        logout_result = self.logout()
        login_result = self.login()


    @Decorators.ensure_connection
    def create_order(self, **kwargs) -> Dict[str, Any]:

        # get and return        
        return self.get(path=settings.ORDER_CREATE_URL, **kwargs)


    @Decorators.ensure_connection
    def confirm_order(self, order_id: str, **kwargs) -> Dict[str, Any]:
        
        # get and return
        return self.get(
            path=settings.ORDER_SUBMIT_URL,
            params={'orderId': order_id}
        )


    @Decorators.ensure_connection
    def get_balance(self, **kwargs) -> Dict[str, Any]:
        
        # get and return
        return self.get(path=settings.BALANCE_URL, **kwargs)


    @Decorators.ensure_connection
    def make_transactions(self, **kwargs) -> Dict[str, Any]:
        
        balance = self.get_balance()
        while float(balance.get('userinfo', {}).get('balance', '0.0')) >= 5.0:
            
            # create order
            order = self.create_order()
            order_id = order.get('data', {}).get('orderId', '')

            # ensure order was created
            if order.get('success', None) and order_id:
                
                # confirm order
                confirmed = self.confirm_order(order_id=order_id)

                if not confirmed.get('success', None):
                    raise RuntimeError(f"Could not confirm order {order_id}.")

            # renew balance
            balance = self.get_balance()
        
        # return new current balance
        return balance


