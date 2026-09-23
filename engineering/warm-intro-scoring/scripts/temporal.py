"""Conservative overlap for already-resolved employer/school/board identities.

Dates retain day/month/year precision. Bounds are guaranteed windows, never
claimed exact start/end dates. Missing end != current. Current means current at
observed_at, not necessarily today. Identity resolution is the caller's job.
"""
import calendar
from datetime import date
import re

def bounds(value):
    if value is None:return None
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}(-\d{2}(-\d{2})?)?',value):raise ValueError('Date must preserve YYYY, YYYY-MM or YYYY-MM-DD precision')
    bits=list(map(int,value.split('-')))
    if len(bits)==3:return (date(*bits),date(*bits))
    if len(bits)==2:
        y,m=bits;return(date(y,m,1),date(y,m,calendar.monthrange(y,m)[1]))
    y=bits[0];return(date(y,1,1),date(y,12,31))

def intervals(row,cutoff):
    start=bounds(row.get('start'));end=bounds(row.get('end'))
    current=row.get('current',False)
    if type(current) is not bool:raise ValueError('current must be boolean')
    if current:
        if end:raise ValueError('Current interval cannot have end date')
        observed=bounds(row.get('observed_at'))
        if observed is None or observed[0]!=observed[1] or observed[0]>cutoff:raise ValueError('Current interval needs day-precision observed_at <= cutoff')
        end=(observed[0],cutoff)
    if not start or not end:return None,None
    if start[0]>end[1]:raise ValueError('Reversed interval')
    loose=(start[0],min(end[1],cutoff))
    guaranteed=(start[1],min(end[0],cutoff))
    return (guaranteed if guaranteed[0]<=guaranteed[1] else None),loose

def overlap(left,right,as_of):
    cutoff=bounds(as_of)
    if cutoff is None or cutoff[0]!=cutoff[1]:raise ValueError('as_of requires day precision')
    a,al=intervals(left,cutoff[0]);b,bl=intervals(right,cutoff[0])
    if a and b:
        start=max(a[0],b[0]);end=min(a[1],b[1])
        if start<=end:return dict(status='verified_overlap',start=start.isoformat(),end=end.isoformat(),precision='conservative_guaranteed_window')
    if al and bl and max(al[0],bl[0])>min(al[1],bl[1]):return dict(status='non_overlap',start=None,end=None)
    return dict(status='unknown',start=None,end=None)
