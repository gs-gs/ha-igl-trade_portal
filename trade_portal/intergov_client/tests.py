import pytest
from unittest import mock

from . import IntergovClient
from .auth import DumbAuth


class MockedResponse:
    def __init__(self, status_code, text=None, json=None):
        self.status_code = status_code
        self.text_resp = text
        self.json_resp = json

    def json(self):
        return self.json_resp

    def text(self):
        return self.text_resp


def test_init():
    ac = DumbAuth()
    with pytest.raises(Exception) as e:
        IntergovClient("banana", {}, ac)
    assert e.value.args[0] == "Country parameter is invalid"

    # fine
    c = IntergovClient("GB", {}, ac)

    with pytest.raises(Exception) as e:  # this is fine because no endpoint provided
        c.retrieve_message("123")
    assert e.value.args[0] == "Message API must be configured first"

    with pytest.raises(Exception) as e:  # this is fine because no endpoint provided
        c.post_message("123")
    assert e.value.args[0] == "Message API must be configured first"

    with pytest.raises(Exception) as e:  # this is fine because no endpoint provided
        c.post_text_document("AU", "body")
    assert e.value.args[0] == "Document API must be configured first"

    with pytest.raises(Exception) as e:  # this is fine because no endpoint provided
        c.post_binary_document("AU", b'body')
    assert e.value.args[0] == "Document API must be configured first"

    with pytest.raises(Exception) as e:  # this is fine because no endpoint provided
        c.retrieve_text_document("123")
    assert e.value.args[0] == "Document API must be configured first"

    with pytest.raises(Exception) as e:  # this is fine because no endpoint provided
        c.retrieve_document("123")
    assert e.value.args[0] == "Document API must be configured first"


@mock.patch("requests.get")
def test_retrieve_message(get_mock):
    ac = DumbAuth()
    c = IntergovClient(
        country="GB",
        endpoints={"message": "http://dumb-domain.tld"},
        auth_class=ac
    )
    get_mock.return_value = MockedResponse(200, json={"lala": "lala"})
    ret = c.retrieve_message("message-sender-ref")

    assert ret == {"lala": "lala"}


@mock.patch("requests.post")
def test_subscribe(get_mock):
    ac = DumbAuth()
    auth_h_name, auth_h_value, exp = ac.get_subscr_auth_header()

    c = IntergovClient(
        country="GB",
        endpoints={"subscription": "http://dumb-domain.tld"},
        auth_class=ac
    )
    get_mock.return_value = MockedResponse(202, text="")
    ret = c.subscribe(
        predicate="a.b.c",
        callback="https://callbacky/"
    )

    get_mock.assert_called_once_with(
        "http://dumb-domain.tld/subscriptions",
        data={
            'hub.callback': "https://callbacky/",
            'hub.topic': "a.b.c",
            'hub.mode': 'subscribe'
        },
        headers={
            auth_h_name: auth_h_value,
        },
    )

    assert ret is True
