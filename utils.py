from pandas.tseries.offsets import BDay
from datetime import date, timedelta

def get_last_work_day(day=date.today()):      
    if day.weekday() == 6:         
        day -= timedelta(days=1)
    if day.weekday() == 0:         
        day -= timedelta(days=2)
    return day

