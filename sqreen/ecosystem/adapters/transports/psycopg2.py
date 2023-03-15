# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
from ....rules import RuleCallback
from ....workflow import Transport


class Psycopg2TransportCallback(RuleCallback):

    def pre(self, instance, args, kwargs, **options):
        try:
            # TODO parse args[0] if provided
            host = kwargs.get("host", "127.0.0.1")
            port = int(kwargs.get("port", 5432))
        except Exception:
            host, port = None, None

        transport = Transport({
            "type": "postgres",
            "host": host,
            "host_port": port,
        })

        context = self.runner.interface_manager.call("context")
        self.runner.interface_manager.call("new_data_out_pre", context, transport)


class Psycopg2TransportAdapter:

    def instrumentation_callbacks(self, runner, storage):
        return [
            Psycopg2TransportCallback.from_rule_dict({
                "name": "ecosystem_psycopg2",
                "rulespack_id": "ecosystem/transport",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "psycopg2",
                    "method": "connect",
                    "strategy": "psycopg2",
                },
                "callbacks": {},
            }, runner, storage)
        ]
