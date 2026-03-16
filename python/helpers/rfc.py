import importlib
import inspect
import json
from typing import Any, TypedDict
import aiohttp
from python.helpers import tls as _tls
from python.helpers import crypto

from python.helpers import dotenv


# Remote Function Call library
# Call function via http request
# Secured by pre-shared key


class RFCInput(TypedDict):
    module: str
    function_name: str
    args: list[Any]
    kwargs: dict[str, Any]


class RFCCall(TypedDict):
    rfc_input: str
    hash: str


async def call_rfc(
    url: str, password: str, module: str, function_name: str, args: list, kwargs: dict
):
    input = RFCInput(
        module=module,
        function_name=function_name,
        args=args,
        kwargs=kwargs,
    )
    call = RFCCall(
        rfc_input=json.dumps(input), hash=crypto.hash_data(json.dumps(input), password)
    )
    result = await _send_json_data(url, call)
    return result


# Only modules whose dotted path starts with one of these prefixes may be
# invoked via RFC. All legitimate callers are internal sentinel modules.
# This blocks calls to os, subprocess, builtins, and third-party packages.
_ALLOWED_MODULE_PREFIXES = (
    "python.helpers.",
    "python.api.",
    "python.tools.",
)


def _assert_module_allowed(module: str) -> None:
    if not any(module.startswith(prefix) for prefix in _ALLOWED_MODULE_PREFIXES):
        raise Exception(
            f"RFC module '{module}' is not in the allowed prefix list. "
            "Only internal sentinel modules may be called via RFC."
        )
    # Every dotted component must be a valid Python identifier to prevent
    # crafted paths that could bypass import restrictions or cause injection.
    if not all(part.isidentifier() for part in module.split(".")):
        raise Exception(
            f"RFC module '{module}' contains invalid identifier components."
        )


async def handle_rfc(rfc_call: RFCCall, password: str):
    if not crypto.verify_data(rfc_call["rfc_input"], rfc_call["hash"], password):
        raise Exception("Invalid RFC hash")

    input: RFCInput = json.loads(rfc_call["rfc_input"])
    _assert_module_allowed(input["module"])
    return await _call_function(
        input["module"], input["function_name"], *input["args"], **input["kwargs"]
    )


async def _call_function(module: str, function_name: str, *args, **kwargs):
    func = _get_function(module, function_name)
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def _get_function(module: str, function_name: str):
    # import module
    imp = importlib.import_module(module)
    # get function by the name
    func = getattr(imp, function_name)
    return func


async def _send_json_data(url: str, data):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(**_tls.get_aiohttp_connector_kwargs())) as session:
        async with session.post(
            url,
            json=data,
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                error = await response.text()
                raise Exception(error)
