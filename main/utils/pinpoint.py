import os
from starlette.middleware import Middleware

# ContextMiddleware signature changed (plugins first), RawContextMiddleware
# keeps the expected (app first) signature for Starlette's Middleware helper.
from starlette_context.middleware import RawContextMiddleware
from pinpointPy import set_agent, monkey_patch_for_pinpoint
from pinpointPy.Fastapi import async_monkey_patch_for_pinpoint, PinPointMiddleWare
from pinpointPy.Fastapi import use_starlette_context
from config import Config
from config.logger import logger


def setup_pinpoint():
    """Initialize PinPoint for FastAPI. Return middleware list."""
    if Config.DEBUG:
        hostname_last = "ttt"
    else:
        HOSTNAME = os.environ.get("HOSTNAME", "unknown")
        LAST_DASH_INDEX = HOSTNAME.rfind("-")
        hostname_last = (
            HOSTNAME[LAST_DASH_INDEX + 1 :] if LAST_DASH_INDEX >= 0 else "default"
        )

    # Set agent according to FastAPI documentation
    # set_agent(app_name, app_type, agent_id, collector_address)
    # PinPoint expects all args as strings; an int agent_id triggers a type error.
    set_agent(
        "llm_blanks" + hostname_last,
        "llm_blanks_recog",
        "tcp:172.16.226.39:10000",
        -1,
        0,
    )

    # Use starlette context (required for FastAPI)
    use_starlette_context()
    monkey_patch_for_pinpoint()
    # AioRedis 打开之后会崩溃, 如果有需要再调试吧
    async_monkey_patch_for_pinpoint(AioRedis=False)

    middleware_list = [Middleware(RawContextMiddleware), Middleware(PinPointMiddleWare)]
    logger.info(
        f"PinPoint initialization successful. middleware_list: {middleware_list}"
    )
    return middleware_list
