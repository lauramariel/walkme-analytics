import logging

logger = logging.getLogger("gunicorn.error")
logger.setLevel(logger.level)

ENV = "prod"

REQUIRED_VALUES = [
    "sId",
    "oId",
    "oName",
    "type",
    "env.browser.name",
    "env.browser.version",
    "env.os.name",
    "wm.euId",
    "wm.env",
    "created_at",
    "ctx.location.protocol",
    "ctx.location.hostname",
    "ctx.location.pathname",
    "ctx.title",
    "wm.userVars.name",
    "wm.userVars.role",
    "wm.userVars.type",
    "wm.userVars.status",
    "wm.userVars.info",
]

TABLE_NAMES = {"started": "StartedSWTs", "tasks": "CompletedTasks"}
