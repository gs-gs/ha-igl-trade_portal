import logging
from http import HTTPStatus

import requests

from .auth import BaseAuthClass

logger = logging.getLogger(__name__)
VERSION = "0.0.3"
VERSION_API = "20200501"


class IntergovClient(object):
    """
    Helper class to perform the intergov API calls easily
    """

    def __init__(self, country: str, endpoints: dict, auth_class: BaseAuthClass):
        """
        Country: 2-letter country code, example: AU, SG, CN

        Endpoints: dict of format
            {
                "document": "https://domain.tld:port",
                "message": "https://domain.tld:port",
                "subscription": "https://domain.tld:port",
            }
        Values are validated only when used, so if you don't use
        document API you may omit the endpoint

        auth_class: instance of class implementing the auth.py::BaseAuthClass
        interface
        """
        country = str(country)
        if len(country) != 2 or country.upper() != country:
            raise Exception("Country parameter is invalid")
        self.COUNTRY = country

        self.auth_class = auth_class
        self.ENDPOINTS = endpoints

    def retrieve_message(self, sender_ref: str) -> dict:
        """
        Retrieves message and returns None or JSON of it's body
        """
        if not isinstance(self.ENDPOINTS.get("message"), str):
            raise Exception("Message API must be configured first")

        auth_h_name, auth_h_value, exp = self.auth_class.get_message_auth_header()
        resp = requests.get(
            self.ENDPOINTS["message"] + f"/message/{sender_ref}",
            headers={
                auth_h_name: auth_h_value,
            },
        )
        if not str(resp.status_code).startswith("2"):
            logger.warning("Non-2xx responce for message retrieval; %s", resp.content)
            return None
        return resp.json()

    def post_message(self, message_json: dict) -> dict:
        """
        Posts a message to message TX API, returns posted message body
        (with sender_ref supposedly to be attached).
        Raises exceptions if any.
        """
        if not isinstance(self.ENDPOINTS.get("message"), str):
            raise Exception("Message API must be configured first")

        auth_h_name, auth_h_value, exp = self.auth_class.get_message_auth_header()
        resp = requests.post(
            self.ENDPOINTS["message"] + "/message",
            json=message_json,
            headers={
                auth_h_name: auth_h_value,
            },
        )

        if resp.status_code != HTTPStatus.CREATED:
            short_text = resp.text[:2000]
            logger.error(
                "Unable to publish message: %s %s",
                resp.status_code,
                short_text
            )
            raise Exception(
                "url: {}, resp: {}".format(
                    self.ENDPOINTS["message"],
                    short_text
                )
            )
        return resp.json()

    def post_text_document(self, receiver: str, document_body) -> dict:
        """
        Accepts str with the document content,
        returns JSON with some document info (at least `multihash` str field)
        """
        if not isinstance(self.ENDPOINTS.get("document"), str):
            raise Exception("Document API must be configured first")

        auth_h_name, auth_h_value, exp = self.auth_class.get_document_auth_header()
        files = {
            'document': ('document.json', document_body)
        }
        resp = requests.post(
            self.ENDPOINTS["document"] + f"/jurisdictions/{receiver}",
            files=files,
            headers={
                auth_h_name: auth_h_value,
            },
        )
        if resp.status_code != HTTPStatus.OK:
            # unexpected but we still need to react somehow
            raise Exception("Unable to post document: %s" % resp.text[:2000])
        return resp.json()

    def post_binary_document(self, receiver: str, document_stream) -> dict:
        if not isinstance(self.ENDPOINTS.get("document"), str):
            raise Exception("Document API must be configured first")

        auth_h_name, auth_h_value, exp = self.auth_class.get_document_auth_header()
        files = {
            'document': ('document.json', document_stream)
        }
        resp = requests.post(
            self.ENDPOINTS["document"] + f"/jurisdictions/{receiver}",
            files=files,
            headers={
                auth_h_name: auth_h_value,
            },
        )
        if resp.status_code != HTTPStatus.OK:
            # unexpected but we still need to react somehow
            raise Exception("Unable to post document: %s" % resp.text[:2000])
        return resp.json()

    def retrieve_text_document(self, *args, **kwargs):
        return self.retrieve_document(*args, **kwargs)

    def retrieve_document(self, document_multihash: str):
        if not isinstance(self.ENDPOINTS.get("document"), str):
            raise Exception("Document API must be configured first")

        auth_h_name, auth_h_value, exp = self.auth_class.get_document_auth_header()
        endpoint = f'{self.ENDPOINTS["document"]}/{document_multihash}'
        resp = requests.get(
            endpoint,
            {
                "as_jurisdiction": str(self.COUNTRY)
            },
            headers={
                auth_h_name: auth_h_value,
            },
        )
        if resp.status_code == 200:
            return resp.content
        else:
            try:
                error = resp.json()
            except Exception:
                error = resp.content.decode("utf-8")
            raise Exception(f"Unable to retrieve document: {resp.status_code}, {error}")

    def subscribe(self, predicate=None, topic=None, callback=None) -> bool:
        if not callback:
            raise Exception("The callback parameter is required")
        if not isinstance(self.ENDPOINTS.get("subscription"), str):
            raise Exception("Subscription API must be configured first")

        auth_h_name, auth_h_value, exp = self.auth_class.get_subscr_auth_header()
        resp = requests.post(
            self.ENDPOINTS["subscription"] + "/subscriptions",
            data={
                'hub.callback': callback,
                'hub.topic': predicate or topic,
                'hub.mode': 'subscribe'
            },
            headers={
                auth_h_name: auth_h_value,
            },
        )
        if resp.status_code != 202:
            raise Exception(
                "Unable to subscribe to {}: {}, {}".format(
                    predicate,
                    resp, resp.text[:2000],
                )
            )
        return True
