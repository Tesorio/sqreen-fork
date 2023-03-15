# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
from ....rules import RuleCallback
from ....workflow import Transport


class PikaTransportCallback(RuleCallback):

    def pre(self, instance, args, kwargs, **options):
        method = args[1] if len(args) > 1 else kwargs.get("method")
        name = getattr(method, "NAME", None)
        if name is None:
            return

        if name == "Basic.Publish":
            op = "out"
        elif name == "Basic.Consume":
            op = "in"
        else:
            return

        transport = Transport({
            "type": "amqp",
            "host": instance.params.host,
            "host_port": instance.params.port,
        })

        context = self.runner.interface_manager.call("context")
        self.runner.interface_manager.call("new_message_{}_pre".format(op),
                                           context, transport)


class PikaTransportAdapter:

    def instrumentation_callbacks(self, runner, storage):
        return [
            PikaTransportCallback.from_rule_dict({
                "name": "ecosystem_pika",
                "rulespack_id": "ecosystem/transport",
                "block": False,
                "test": False,
                "hookpoint": {
                    "klass": "pika.connection::Connection",
                    "method": "_send_method",
                },
                "callbacks": {},
            }, runner, storage)
        ]
