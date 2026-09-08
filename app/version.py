# Single source of truth for the app version. setup.py reads it from
# this file with a regex, so keep APP_VERSION a plain string literal.
APP_VERSION = "1.3.1"

USER_AGENT = f"CoomerDL/{APP_VERSION}"
