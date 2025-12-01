import datetime
from zoneinfo import ZoneInfo

from src.utils import agent_function_tool


@agent_function_tool
def get_current_datetime() -> str:
    """
    Get the current time as a string in ISO 8601 format for Vietnam (ICT).
    """
    vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    current_time = datetime.datetime.now(tz=vn_tz).isoformat()
    output = f"The current time in Vietnam (ICT) is: {current_time}"

    return output
