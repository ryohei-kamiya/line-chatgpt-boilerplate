import sys
from logging import getLogger, StreamHandler, Formatter, basicConfig, Logger


class LoggerFactory:
    _loggers = {}
    _available_log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]
    _log_level = "WARNING"

    @classmethod
    def get_user_log_level(cls):
        argv = sys.argv
        for i, arg in enumerate(argv):
            if arg == "--log":
                if i + 1 < len(argv):
                    if argv[i + 1].upper() in cls._available_log_levels:
                        cls._log_level = argv[i + 1]
                        del sys.argv[i + 1]
                        del sys.argv[i]
                        break
        else:
            return None
        return cls._log_level

    @classmethod
    def get_logger(cls, name="default logger", log_level="WARNING") -> Logger:
        if len(cls._loggers.keys()) == 0:
            basicConfig(stream=sys.stderr)
        user_log_level = cls.get_user_log_level()
        log_level = user_log_level if user_log_level else log_level
        if cls._loggers.get(name) is None:
            handler = StreamHandler()
            formatter = Formatter(
                "%(asctime)s [%(levelname)s] %(filename)s(%(lineno)d), in %(funcName)s, %(message)s"
            )
            handler.setFormatter(formatter)
            logger = getLogger(name)
            logger.setLevel(log_level)
            logger.addHandler(handler)
            logger.propagate = False
            cls._loggers[name] = logger
        return cls._loggers[name]
