"""Keep system SSH/curl/rsync out of the Python runtime's shared libraries."""
import os


def host_tool_environment(base=None):
    environment = dict(os.environ if base is None else base)
    environment.pop('LD_LIBRARY_PATH', None)
    environment.pop('LD_PRELOAD', None)
    # Retain user-installed tools (e.g. gh) after the host system executables.
    environment['PATH'] = '/usr/bin:/bin:/usr/local/bin:' + environment.get('PATH', '')
    return environment
