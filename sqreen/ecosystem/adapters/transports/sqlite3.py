# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
from ....rules import RuleCallback
from ....workflow import Transport


class SQLite3TransportCallback(RuleCallback):

    def pre(self, instance, args, kwargs, **options):
        transport = Transport({
            "type": "sqlite",
            "host": "127.0.0.1",
        })

        context = self.runner.interface_manager.call("context")
        self.runner.interface_manager.call("new_data_out_pre", context, transport)


class SQLite3TransportAdapter:

    def instrumentation_callbacks(self, runner, storage):
        return [
            SQLite3TransportCallback.from_rule_dict({
                "name": "ecosystem_sqlite3",
                "rulespack_id": "ecosystem/transport",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "sqlite3.dbapi2",
                    "method": "connect",
                    "strategy": "DBApi2"
                },
                "callbacks": {},
            }, runner, storage)
        ]
