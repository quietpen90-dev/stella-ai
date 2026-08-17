"""STELLA application entry point.

The HTTP implementation is kept in server.py. Supporting configuration and
service helpers live in dedicated modules.
"""
import server  # noqa: F401  # server.py starts the configured HTTP service
