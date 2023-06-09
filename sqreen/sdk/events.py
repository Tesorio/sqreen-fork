# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
import logging
import traceback
from datetime import datetime

from ..actions import BaseAction
from ..runtime_storage import RuntimeStorage, runtime
from ..utils import HAS_TYPING, is_string, naive_dt_to_utc, now

if HAS_TYPING:
    from typing import Mapping, MutableMapping, Optional, Set


LOGGER = logging.getLogger(__name__)


_SQREEN_EVENT_PREFIX = "sq."

_TRACK_OPTIONS_FIELDS = frozenset(
    ["properties", "user_identifiers", "timestamp", "collect_body"]
)

_TRACK_PAYLOAD_SECTIONS = ("request", "response", "headers", "local")

STACKTRACE_EVENTS = set()  # type: Set[str]

_MAX_EVENT_PROPERTIES = 16


def _track_unsafe(event, options, storage=runtime, source="track"):
    # type: (str, MutableMapping, RuntimeStorage, str) -> bool
    """Track an SDK event.

    This function is used internally in the agent to send built-in SDK events,
    e.g. output of security actions. It does not perform any check and is not
    exposed to the user.
    """
    if "timestamp" not in options:
        options["timestamp"] = now()
    payload_sections = set(_TRACK_PAYLOAD_SECTIONS)
    if options.get("collect_body", False):
        payload_sections.add("params")
    storage.observe(
        "sdk",
        [source, options["timestamp"], event, options],
        payload_sections=payload_sections,
        report=True,
    )
    return True


def track(event, options=None, storage=runtime):
    # type: (str, Optional[Mapping], RuntimeStorage) -> bool
    """Track an SDK event."""
    # Check event type.
    if not is_string(event):
        raise TypeError(
            "event name must be a string, not {}".format(
                event.__class__.__name__
            )
        )
    # Check event name.
    if event.startswith(_SQREEN_EVENT_PREFIX):
        LOGGER.warning(
            "Event names starting with %r are reserved, "
            "event %r has been ignored",
            _SQREEN_EVENT_PREFIX,
            event,
        )
        return False
    if options is None:
        options = {}
    else:
        options = dict(options)
    # Check option keys.
    for option_key in list(options):
        if option_key not in _TRACK_OPTIONS_FIELDS:
            LOGGER.warning("Invalid option key %r, skipped", option_key)
            del options[option_key]
    timestamp = options.get("timestamp")
    if timestamp is not None:
        if not isinstance(timestamp, datetime):
            raise TypeError(
                "timestamp option must be a datetime object, not {}".format(
                    event.__class__.__name__
                )
            )
        if timestamp.tzinfo is None:
            LOGGER.info("Event %r timestamp is not timezone-aware, default to UTC",
                        event)
            options["timestamp"] = timestamp = naive_dt_to_utc(timestamp)

    properties = options.get("properties")
    # Check the number of properties.
    if properties and len(properties) > _MAX_EVENT_PROPERTIES:
        LOGGER.warning(
            "Event %r has %d properties, "
            "only the first %d ones will be reported",
            event,
            len(properties),
            _MAX_EVENT_PROPERTIES,
        )
        options["properties"] = dict(
            sorted(properties.items())[:_MAX_EVENT_PROPERTIES]
        )
    # Store stacktrace if required.
    if event in STACKTRACE_EVENTS:
        LOGGER.debug("Stacktrace recorded by for event %s", event)
        options["stacktrace"] = traceback.format_stack()
    # Body requested
    options["collect_body"] = bool(options.get("collect_body"))
    # Warn about different user identifiers
    user_identifiers = options.get("user_identifiers")
    if user_identifiers:
        global_user_identifiers = storage.get_request_store().get("user_identifiers")
        if global_user_identifiers is not None and user_identifiers != global_user_identifiers:
            LOGGER.warning(
                "sqreen.identify and sqreen.track have been called "
                "with different user_identifiers values"
            )

    return _track_unsafe(event, options, storage=storage)


def track_action(action, output, storage=runtime):
    # type: (BaseAction, Mapping, RuntimeStorage) -> bool
    """Track an action output."""
    if not action.send_response:
        return False
    return _track_unsafe(
        "sq.action.{}".format(action.name),
        {
            "properties": {"output": output, "action_id": action.iden},
            "collect_body": True,
        },
        storage=storage,
    )
