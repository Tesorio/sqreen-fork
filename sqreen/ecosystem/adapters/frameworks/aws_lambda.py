# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
""" AWS Lambda Adapter
"""
import base64
import logging
import sys

from ....exceptions import SqreenException
from ....frameworks.base import BaseRequest, BaseResponse
from ....rules import RuleCallback
from ....rules_callbacks import (
    BindingAccessorCounter,
    BindingAccessorProvideData,
    CountHTTPCodesCB,
    RecordRequestContext,
)
from ....rules_callbacks.sqreen_error_page import BaseSqreenErrorPage
from ....utils import HAS_TYPING

if HAS_TYPING:
    from typing import FrozenSet, Set


LOGGER = logging.getLogger(__name__)

UNSUPPORTED_LAMBDA_EVENTS = set()  # type: Set[FrozenSet[str]]


class UnsupportedAWSLambdaEvent(SqreenException):

    def __init__(self, event):
        self.event = event

    def exception_infos(self):
        return {
            "event": self.event
        }


class AWSLambdaProxyV2Request(BaseRequest):
    """
    AWS Lambda Proxy Integration v2 event.
    """

    def __init__(self, event, storage=None):
        super(AWSLambdaProxyV2Request, self).__init__(storage=storage)
        self.event = event
        self.rc = event.get("requestContext")

    @property
    def remote_addr(self):
        return self.rc.get("http", {}).get("sourceIp")

    @property
    def hostname(self):
        return self.rc.get("domainName")

    @property
    def method(self):
        return self.event.get("httpMethod")

    @property
    def referer(self):
        return self.get_raw_header("referer")

    @property
    def client_user_agent(self):
        return self.rc.get("http", {}).get("userAgent")

    @property
    def path(self):
        return self.rc.get("path")

    @property
    def request_uri(self):
        return "?".join((self.event.get("rawPath"), self.event.get("rawQueryString")))

    @property
    def scheme(self):
        return self.event.get("headers", {}).get("x-forwarded-proto", "http")

    @property
    def server_port(self):
        return self.event.get("headers", {}).get("x-forwarded-port", "http")

    @property
    def remote_port(self):
        return None

    @property
    def view_params(self):
        return self.event.get("pathParameters")

    @property
    def body(self):
        isBase64Encoded = self.event.get("isBase64Encoded")
        body = self.event.get("body")
        if isBase64Encoded and body:
            return base64.b64decode(body)
        return body

    @property
    def form_params(self):
        # TODO
        return None

    @property
    def query_params(self):
        params = self.event.get("multiValueQueryStringParameters")
        return params if params is not None else dict()

    @property
    def cookies_params(self):
        return self.event.get("cookies")

    @property
    def raw_headers(self):
        return self.event.get("headers")


class AWSLambdaProxyV1Request(BaseRequest):
    """
    AWS Lambda Proxy Integration event.
    """

    def __init__(self, event, storage=None):
        super(AWSLambdaProxyV1Request, self).__init__(storage=storage)
        self.event = event
        self.rc = event.get("requestContext")

    @property
    def remote_addr(self):
        return self.rc.get("identity", {}).get("sourceIp")

    @property
    def hostname(self):
        return self.rc.get("domainName")

    @property
    def method(self):
        return self.event.get("httpMethod")

    @property
    def referer(self):
        return self.get_raw_header("referer")

    @property
    def client_user_agent(self):
        return self.rc.get("identity", {}).get("userAgent")

    @property
    def path(self):
        return self.event.get("path")

    @property
    def scheme(self):
        return self.event.get("headers", {}).get("X-Forwarded-Proto", "http")

    @property
    def server_port(self):
        return self.event.get("headers", {}).get("X-Forwarded-Port")

    @property
    def remote_port(self):
        # No remote port in the event
        return None

    @property
    def view_params(self):
        return self.event.get("pathParameters")

    @property
    def body(self):
        isBase64Encoded = self.event.get("isBase64Encoded")
        body = self.event.get("body")
        if isBase64Encoded and body:
            return base64.b64decode(body)
        return body

    @property
    def form_params(self):
        # TODO
        return None

    @property
    def query_params(self):
        params = self.event.get("multiValueQueryStringParameters")
        return params if params is not None else dict()

    @property
    def cookies_params(self):
        return None

    @property
    def raw_headers(self):
        # TODO header case
        return self.event.get("headers")


class AWSLambdaProxyV1Response(BaseResponse):

    def __init__(self, response):
        self.res = response

    @property
    def status_code(self):
        return self.res.get("statusCode")

    @property
    def content_type(self):
        # TODO header case
        return self.res.get("headers", {}).get("Content-Type")

    @property
    def content_length(self):
        # TODO header case
        cl = self.res.get("headers", {}).get("Content-Length")
        if cl is not None:
            try:
                return int(cl)
            except Exception:
                pass
        return None


class RecordRequestContextAWSLambda(RecordRequestContext):

    def pre(self, instance, args, kwars, **options):
        event = args[0]
        version = event.get("version")
        if version == "2.0":
            self._store_request(AWSLambdaProxyV2Request(event))
        elif version == "1.0" or "httpMethod" in event:
            self._store_request(AWSLambdaProxyV1Request(event))
        else:
            # Very basic filter to limit sending too many exceptions
            event_type = frozenset(event.keys())
            if event_type not in UNSUPPORTED_LAMBDA_EVENTS:
                UNSUPPORTED_LAMBDA_EVENTS.add(event_type)
                raise UnsupportedAWSLambdaEvent(event)


class RecordResponseAWSLambda(RuleCallback):

    INTERRUPTIBLE = False

    def _record_response(self, options):
        result = options.get("result")
        if result:
            response = AWSLambdaProxyV1Response(result)
            self.storage.store_response(response)

    def post(self, instance, args, kwargs, **options):
        self._record_response(options)

    def failing(self, instance, args, kwargs, **options):
        self._record_response(options)


class SqreenErrorPageAWSLambda(BaseSqreenErrorPage):

    def failing(self, instance, args, kwargs, exc_info=None, **options):
        ret = self.handle_exception(exc_info[1])
        if ret is not None:
            status_code, body, headers = ret
            resp = {
                "statusCode": status_code,
                "headers": headers,
                "isBase64Encoded": False,
                "body": body,
            }
            return {
                "status": "override",
                "new_return_value": resp,
            }


class ExecuteRunner(RuleCallback):

    INTERRUPTIBLE = False

    def post(self, instance, args, kwars, **options):
        self._flush()

    def failing(self, instance, args, kwars, **options):
        self._flush()

    def _flush(self):
        self.runner.handle_messages(block=False)
        self.runner.aggregate_observations()
        self.runner.publish_metrics()
        self.runner.deliverer.drain(resiliently=False)
        # the heartbeat notifies the end of the request
        self.runner.do_heartbeat()


class AWSLambdaFrameworkAdapter:

    def instrumentation_callbacks(self, runner, storage):
        # The module must be similar to the strategy MODULE_NAME
        module = "__main__" if sys.version_info[:2] != (3, 7) else "bootstrap"
        return [
            RecordRequestContextAWSLambda.from_rule_dict({
                "name": "ecosystem_aws_lambda_request_context",
                "rulespack_id": "ecosystem/framework",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "callbacks": {},
                "priority": 20,
            }, runner, storage),
            BindingAccessorProvideData.from_rule_dict({
                "name": "ecosystem_aws_lambda_provide_data",
                "rulespack_id": "ecosystem/framework",
                "conditions": {
                    "pre": {
                        "%and": [
                            "#.request",
                        ]
                    },
                    "post": {
                        "%and": [
                            "#.response",
                        ]
                    },
                },
                "data": {
                    "values": [
                        ["pre", [
                            ["server.request.client_ip", "#.client_ip"],
                            ["server.request.method", "#.method"],
                            ["server.request.uri.raw", "#.request_uri"],
                            ["server.request.headers.no_cookies", "#.headers_no_cookies"],
                            ["server.request.cookies", "#.cookies_params"],
                            ["server.request.query", "#.query_params"],
                            ["server.request.body", "#.body_params"],
                            ["server.request.body.raw", "#.body"],
                            ["server.request.body.files_field_names", "#.files_field_names"],
                            ["server.request.body.filenames", "#.filenames"],
                            ["server.request.body.combined_file_size", "#.combined_file_size"],
                            ["server.request.path_params", "#.view_params"],
                        ]],
                        ["post", [
                            ["server.response.status", "#.response.status_code"],
                            ["server.response.headers.no_cookies", "#.response.headers_no_cookies"],
                            ["server.response.body.raw", "#.response.body"],
                        ]]
                    ]
                },
                "block": True,
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "priority": 80,
            }, runner, storage),
            RecordResponseAWSLambda.from_rule_dict({
                "name": "ecosystem_aws_lambda_record_response",
                "rulespack_id": "ecosystem/framework",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "priority": 90,
            }, runner, storage),
            SqreenErrorPageAWSLambda.from_rule_dict({
                "name": "ecosystem_aws_lambda_error_page",
                "rulespack_id": "ecosystem/framework",
                "block": True,
                "test": False,
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "priority": 100,
            }, runner, storage),
            CountHTTPCodesCB.from_rule_dict({
                "name": "ecosystem_aws_lambda_legacy_http_code",
                "rulespack_id": "ecosystem/framework",
                "callbacks": {},
                "conditions": {
                    "failing": {
                        "%and": [
                            "#.response"
                        ]
                    },
                    "post": {
                        "%and": [
                            "#.response"
                        ]
                    },
                    "pre": {}
                },
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "metrics": [
                    {
                        "kind": "Sum",
                        "name": "http_code",
                        "period": 60
                    }
                ],
                "priority": 60,
            }, runner, storage),
            BindingAccessorCounter.from_rule_dict({
                "name": "ecosystem_aws_lambda_ba_normal_http_counter",
                "rulespack_id": "ecosystem/framework",
                "callbacks": {},
                "conditions": {
                    "failing": {
                        "%and": [
                            "#.response",
                            {
                                "%lt": [
                                    "#.response.status_code",
                                    400
                                ]
                            }
                        ]
                    },
                    "post": {
                        "%and": [
                            "#.response",
                            {
                                "%lt": [
                                    "#.response.status_code",
                                    400
                                ]
                            }
                        ]
                    },
                    "pre": {}
                },
                "data": {
                    "values": [
                        "#.client_ip",
                        "#.response.status_code",
                    ]
                },
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "metrics": [
                    {
                        "kind": "Sum",
                        "name": "ip-http_code",
                        "period": 60
                    }
                ],
                "priority": 60,
            }, runner, storage),
            BindingAccessorCounter.from_rule_dict({
                "name": "ecosystem_aws_lambda_ba_error_http_counter",
                "rulespack_id": "ecosystem/framework",
                "callbacks": {},
                "conditions": {
                    "failing": {
                        "%and": [
                            "#.response",
                        ]
                    },
                    "post": {
                        "%and": [
                            "#.response",
                            {
                                "%gte": [
                                    "#.response.status_code",
                                    400
                                ]
                            },
                            {
                                "%lt": [
                                    "#.response.status_code",
                                    600
                                ]
                            }
                        ]
                    },
                    "pre": {}
                },
                "data": {
                    "values": [
                        "#.client_ip",
                        "#.response.status_code",
                        "#.path"
                    ]
                },
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "metrics": [
                    {
                        "kind": "Sum",
                        "name": "ip-http_code-path",
                        "period": 60
                    }
                ],
                "priority": 60,
            }, runner, storage),
            ExecuteRunner.from_rule_dict({
                "name": "ecosystem_aws_lambda_execute_runner",
                "rulespack_id": "ecosystem/transport",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "{}::None".format(module),
                    "method": "handle_event_request",
                    "strategy": "aws_lambda",
                },
                "callbacks": {},
                "priority": 10,
            }, runner, storage),
        ]
