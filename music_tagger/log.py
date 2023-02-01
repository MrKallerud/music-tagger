class Color:
    BLUE      = "\033[94m"
    BOLD      = "\033[1m"
    CLEAR     = "\033[0m"
    CYAN      = "\033[96m"
    GREEN     = "\033[92m"
    HEADER    = "\033[95m"
    RED       = "\033[91m"
    UNDERLINE = "\033[4m"
    YELLOW    = "\033[93m"

class Log:
    level = str

    # Levels
    INFO = 0
    ERROR = 1
    WARNING = 2
    DEBUG = 3
    __ALL_LVLS = [INFO,ERROR,WARNING,DEBUG]

    # Settings
    __SELECTED_LVL = INFO

    @staticmethod
    def config(lvl: level = None) -> None:
        if lvl is not None:
            if lvl not in Log.__ALL_LVLS: raise ValueError(f"{lvl} is not a valid level")
            Log.__SELECTED_LVL = lvl

    @staticmethod
    def get_format(lvl_name: str, message: str, color: str = ""):
        return f"{color}[{lvl_name}]{Color.CLEAR} {message}"

    @staticmethod
    def info(message: str, lvl_name: str = "info", color: Color = Color.CYAN):
        if Log.INFO > Log.__SELECTED_LVL: return
        # TODO: Print to file
        print(Log.get_format(lvl_name, message, color))

    @staticmethod
    def error(message: str):
        if Log.ERROR > Log.__SELECTED_LVL: return
        # TODO: Print to file
        print(Log.get_format("error", message, Color.RED))

    @staticmethod
    def warning(message: str):
        if Log.WARNING > Log.__SELECTED_LVL: return
        # TODO: Print to file
        print(Log.get_format("warning", message, Color.YELLOW))

    @staticmethod
    def debug(message: str):
        if Log.DEBUG > Log.__SELECTED_LVL: return
        # TODO: Print to file
        print(Log.get_format("debug", message))
