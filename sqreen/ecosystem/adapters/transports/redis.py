# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
from ....rules import RuleCallback
from ....workflow import Transport


class RedisTransportCallback(RuleCallback):

    def pre(self, instance, args, kwargs, **options):
        try:
            host = kwargs["host"]
            port = kwargs["port"]
        except Exception:
            host, port = None, None

        transport = Transport({
            "type": "redis",
            "host": host,
            "host_port": port,
        })

        context = self.runner.interface_manager.call("context")
        self.runner.interface_manager.call("new_data_out_pre", context, transport)


class RedisTransportAdapter:

    def instrumentation_callbacks(self, runner, storage):
        return [
            RedisTransportCallback.from_rule_dict({
                "name": "ecosystem_redis",
                "rulespack_id": "ecosystem/transport",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "redis.connection::Connection",
                    "method": "__init__",
                },
                "callbacks": {},
            }, runner, storage)
        ]
