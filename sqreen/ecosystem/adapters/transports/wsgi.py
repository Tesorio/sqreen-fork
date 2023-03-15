# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
""" WSGI Transport Adapter
"""

from ....rules import RuleCallback
from ....workflow import Transport


class WSGITransportCallback(RuleCallback):

    def pre(self, instance, args, kwargs, **options):
        request = self.storage.get_current_request()
        if request is None:
            return
        transport = Transport({
            "type": "http",
            "client_ip": request.client_ip,
            "hostname": request.hostname,
            "server_port": request.server_port,
            "tracing_identifier": request.request_headers["HTTP_X_SQREEN_TRACE_IDENTIFIER"],
        })
        context = self.runner.interface_manager.call("context")
        self.runner.interface_manager.call("new_data_in_pre", context, transport)
