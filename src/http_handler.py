from __future__ import annotations
from base64 import b64encode
from inspect import signature
from json.decoder import JSONDecodeError
from pathlib import Path
from pydantic import BaseSettings
from typing import Optional, Union, Dict, List, Any
from urllib.parse import urlparse, urljoin, ParseResult

import aiohttp
import datetime as dt
import requests

from utils import Decorators


_JSONValue = Union[str, int, float, bool, None, dt.date, dt.datetime, Any]
_JSONDict = Dict[str, _JSONValue]
JSONResponse = Union[_JSONDict, List[Union[_JSONDict, _JSONValue]]]


class Defaults(BaseSettings):
    PAGE_SIZE: int = 50
    TIME_OUT: int = 60
    DATE_FROM: dt.date = dt.date.today()
    
    class Extra:
        ...

class HTTPClient:
    __name__: Optional[str] = None

    def __init__(
        self,
        *,
        url: Union[str, Path, ParseResult],
        session: Optional[Union[
            requests.Session,
            aiohttp.ClientSession
        ]] = None
    ) -> None:
        
        # base
        self.url = url
        self.session = session
        
        # needs
        if isinstance(url, ParseResult):
            self.client_url = url
        else:
            self.client_url = urlparse(url)
            
        # self.client_url.geturl() = url

        # unset
        self.headers = None

        # defaults
        self.defaults = Defaults()

    def __str__(self) -> str:
        return f'{self.__name__} Client for {self.client_url.geturl()}'

    def __repr__(self) -> str:
        try:
            return "{class_}({params})".format(
                class_=self.__class__.__name__,
                params=', '.join([
                    "{attr_name}={quote}{attr_val}{quote}".format(
                        attr_name=attr,
                        quote="'" if type(getattr(self, attr)) == str else "",
                        attr_val=getattr(self, attr)
                    )
                    for attr in signature(self.__init__).parameters
                ])
            )
        except:
            return super().__repr__()


class OAuthBase(HTTPClient):

    def __init__(
        self,
        *,
        url: Union[str, Path, ParseResult],
        username: str,
        pwd: str,
        session: Optional[Union[
            requests.Session,
            aiohttp.ClientSession
        ]] = None
    ) -> None:
        super().__init__(url=url, session=session)

        self.username = username
        self.pwd = b64encode(pwd.encode('utf-8'))

    def __eq__(self, o: OAuthClient) -> bool:
        return self.url == o.url and self.username == o.username
    
    def __ne__(self, o: OAuthClient) -> bool:
        return self.url == o.url or self.username != o.username


class OAuthClient(OAuthBase):

    @property
    def is_connected(self):
        """ Overwrite this property according to your need. """
        raise NotImplementedError("This method must be overloaded to work.")

    @property
    def session_expired(self):
        """ Check if session has expired and if is necessary to reconnect."""
        raise NotImplementedError("This method must be overloaded to work.")

    def login(self) -> None:
        """ Overwrite this method according to your need. """
        raise NotImplementedError("This method must be overloaded to work.")

    def logout(self) -> None:
        """ Overwrite this method according to your need. """
        raise NotImplementedError("This method must be overloaded to work.")

    def relogin(self) -> None:
        """ Overwrite this method according to your need. """
        raise NotImplementedError("This method must be overloaded to work.")

    def __enter__(self, *args, **kwargs) -> OAuthClient:
        self.start_session()
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.close_session()

    def start_session(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # login
        self.login()

    def refresh_session(self) -> None:
        self.session.headers.update(self.headers)

    def close_session(self):
        self.logout()
        if self.session != None:
            self.session.close()
        self.session = None

    @Decorators.ensure_session
    def get(
        self,
        url: Optional[Union[str, Path, ParseResult]] = None,
        path: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Union[JSONResponse, requests.Response]:
        """
        Sends a GET request to visma url.

        :param path: path to add to URL for the new :class:`Request` object.
        :param params: (optional) Dictionary, list of tuples or bytes to send
            in the query string for the :class:`Request`.
        :param **kwargs: Optional arguments that ``request`` takes.
        :return: :class:`dict` object
        :rtype: dict
        """

        # prepare url
        url = url or urljoin(self.client_url.geturl(), path)

        # consulting nettime
        response = self.session.get(url=url, params=params, **kwargs)

        # if session was closed, reconect client and try again
        if response.status_code == 401 and self.session_expired:
            self.relogin()
            return self.get(path=path, params=params, **kwargs)

        # raise if was an error
        if response.status_code not in range(200, 300):
            raise ConnectionError({
                "status": response.status_code,
                "detail": response.text
            })

        # if request is stream type, return all response
        if kwargs.get("stream"):
            return response

        # to json
        return response.json()

    @Decorators.ensure_session
    def post(
        self,
        url: Optional[Union[str, Path, ParseResult]] = None,
        path: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        get_headers: Optional[bool] = None,
        **kwargs
    ):
        """
        Sends a POST request to visma url.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json data to send in the body of the 
            :class:`Request`.
        :param **kwargs: Optional arguments that ``request`` takes.
        :return: :class:`dict` object
        :rtype: dict
        """

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
            return getattr(response, "headers", {})

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