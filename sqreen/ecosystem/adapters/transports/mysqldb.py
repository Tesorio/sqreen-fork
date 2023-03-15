# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
from ....rules import RuleCallback
from ....workflow import Transport


class MySQLDbTransportCallback(RuleCallback):

    def pre(self, instance, args, kwargs, **options):
        try:
            host = kwargs.get("host")
            if host is None:
                if args:
                    host = args[0]
                else:
                    host = "127.0.0.1"
            port = int(kwargs.get("port", 3306))
        except Exception:
            host, port = None, None

        transport = Transport({
            "type": "mysql",
            "host": host,
            "host_port": port,
        })

        context = self.runner.interface_manager.call("context")
        self.runner.interface_manager.call("new_data_out_pre", context, transport)


class MySQLDbTransportAdapter:

    def instrumentation_callbacks(self, runner, storage):
        return [
            MySQLDbTransportCallback.from_rule_dict({
                "name": "ecosystem_mysqldb",
                "rulespack_id": "ecosystem/transport",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "MySQLdb",
                    "method": "connect",
                    "strategy": "DBApi2",
                },
                "callbacks": {},
            }, runner, storage)
        ]
