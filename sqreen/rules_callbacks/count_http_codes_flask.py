# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
""" Count http codes for flask framework
"""
import logging

from ..rules import RuleCallback

LOGGER = logging.getLogger(__name__)


class CountHTTPCodesCBFlask(RuleCallback):

    INTERRUPTIBLE = False

    def post(self, instance, args, kwargs, result=None, **options):
        """ Recover the status code and update the http_code metric
        """
        response = result
        status_code = response.status_code
        self.record_observation("http_code", str(status_code), 1)

        return {}

    def failing(self, instance, args, kwargs, **options):
        """ Recover the status code and update the http_code metric
        """
        self.record_observation("http_code", "500", 1)

        return {}
