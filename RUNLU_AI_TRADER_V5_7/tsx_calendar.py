"""Rule-based TSX regular holiday estimates, NOT an authoritative exchange calendar."""
from datetime import date,timedelta

def nth_weekday(year,month,weekday,n):
    first=date(year,month,1)
    return first+timedelta(days=(weekday-first.weekday())%7+7*(n-1))

def last_monday_before(year,month,day):
    target=date(year,month,day)
    return target-timedelta(days=(target.weekday()-0)%7)

def easter(year):
    a=year%19;b=year//100;c=year%100;d=b//4;e=b%4;f=(b+8)//25;g=(b-f+1)//3
    h=(19*a+b-d-g+15)%30;i=c//4;k=c%4;l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451
    month=(h+l-7*m+114)//31;day=(h+l-7*m+114)%31+1
    return date(year,month,day)

def observed(day):
    if day.weekday()==5:return day+timedelta(days=2)
    if day.weekday()==6:return day+timedelta(days=1)
    return day

def estimated_holidays(year):
    if not isinstance(year,int) or not 2000<=year<=2100:raise ValueError('year out of range')
    christmas=observed(date(year,12,25))
    boxing=observed(date(year,12,26))
    if boxing==christmas:boxing+=timedelta(days=1)
    holidays={observed(date(year,1,1)):'New Year (observed)',
        nth_weekday(year,2,0,3):'Family Day',
        easter(year)-timedelta(days=2):'Good Friday',
        last_monday_before(year,5,24):'Victoria Day',
        observed(date(year,7,1)):'Canada Day (observed)',
        nth_weekday(year,8,0,1):'Civic Holiday',
        nth_weekday(year,9,0,1):'Labour Day',
        nth_weekday(year,10,0,2):'Thanksgiving',
        christmas:'Christmas (observed)',boxing:'Boxing Day (observed)'}
    return holidays

def classify_weekdays(days):
    """Categorize gap days, preserving all unverified days for review."""
    result=[]
    for value in days:
        day=date.fromisoformat(value)
        if day.weekday()>=5:raise ValueError('not a weekday')
        holiday=estimated_holidays(day.year).get(day)
        result.append({'date':value,'classification':'ESTIMATED_HOLIDAY' if holiday else 'UNEXPLAINED_WEEKDAY',
                       'holiday_name':holiday,'verified_exchange_schedule':False})
    return result
