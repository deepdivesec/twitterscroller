from datetime import timedelta, datetime
from django.shortcuts import render
import math
import configparser
import psycopg2
from sys import exit
from functools import lru_cache

config = configparser.ConfigParser()
# when out of testbed, ../conf.ini
# need better way of referencing relative path
config.read('../conf.ini')

pghost = config['Postgres']['host']
pguser = config['Postgres']['user']
pgpass = config['Postgres']['password']
pgdb = config['Postgres']['db']
tweetaccounts = config['Twitter']['accounts']
tzoffset = int(config['Timezone']['tzoffset'])
interval = config['Postgres']['interval']

# Create your views here.
def index(request):
    context = dict()
    return render(request, "twitter/index.html", context=context)

def scroller(request):
    #if request.method == "GET":
    # pull tweets for the last 5 minutes and pass them to template
    data = list()
    refresh = int(int(interval) / 2 * 60)
    try:
        conn = psycopg2.connect(f"dbname={pgdb} user={pguser} password={pgpass} host={pghost}")
    except Exception as e:
        print(e)
        exit("Unable to connect to postgres database!")
    cur = conn.cursor()
    cur.execute(
        f"SELECT accname, hashtags, symbols, ttext, created from twitter where created >= CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - INTERVAL '{interval} minutes' ORDER BY created DESC;")
    tweets = cur.fetchall()
    for tweet in tweets:
        local = tweet[4] + timedelta(hours=tzoffset)
        twDict = {"account": tweet[0], "hashtags": tweet[1], "symbols": tweet[2], "ttext": tweet[3], "created": local}
        data.append(twDict)
    # 12 tweets displayed / minute
    # expand the dictionary to accomodate this
    runMins = round(int(interval) / 2)
    tweetsNeeded = runMins * 12

    # 4 tweets fit on a page, if less than this, don't duplicate tweets, if not duplicate
    #print("Initial length: ", len(data))
    if len(data) > 4:
        dataLength = len(data)
        multiplier = round(tweetsNeeded / dataLength)
        data = data * multiplier
    #print("With multplier: ", len(data))
    return render(request, "twitter/scroller.html", {'refresh': refresh, 'interval': interval, "data": data})

#@lru_cache(maxsize=2)
def feeds(request):
    """Display a list of feeds from the config file with additional information"""
    # also pull additional information on them from db and display it
    # get info from config file
    data = dict()
    # {barrons: {name: barrons, id: barrons, description: <description>, url: <url>, followers: <num followers>}}
    tweetList0 = tweetaccounts.splitlines()
    tweetList = [item for item in tweetList0 if item]
    try:
        conn = psycopg2.connect(f"dbname={pgdb} user={pguser} password={pgpass} host={pghost}")
    except Exception as e:
        print(e)
        exit("Unable to connect to postgres database!")
    cur = conn.cursor()
    # select distinct on (acctid), tjson from twitter where acctid in {list from conf.ini}
    cur.execute(f"SELECT DISTINCT ON (acctid) acctid, tjson from twitter where acctid in {tuple(tweetList)};")
    accounts = cur.fetchall()
    for item in accounts:
        acctName = item[0]
        acctDict = {"username": item[1]["user"]["name"], "screenname": item[1]["user"]["screen_name"],
                    "description": item[1]["user"]["description"], "url": item[1]["user"]["url"],
                    "followers": item[1]["user"]["followers_count"], "totaltweets": item[1]["user"]["statuses_count"]}
        data.update({acctName: acctDict})

    return render(request, "twitter/feeds.html", {'data': data})

#------------------------
# testbed for code
# try:
#     conn = psycopg2.connect(f"dbname={pgdb} user={pguser} password={pgpass} host={pghost}")
# except Exception as e:
#     print(e)
#     exit("Unable to connect to postgres database!")
# cur = conn.cursor()
# utcnow = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
# # select distinct on (acctid), tjson from twitter where acctid in {list from conf.ini}
# cur.execute(f"SELECT accname, hashtags, symbols, ttext, created from twitter where created >= CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - INTERVAL '5 minutes';")
# accounts = cur.fetchall()
# for account in accounts:
#     #print(account)
#     print("acct: ", account[0])
#     print("hashtags: ", account[1])
#     print("symbols: ", account[2])
#     print("ttext: ", account[3])
#     local = account[4] + timedelta(hours=tzoffset)
#     print("created: ", local)
#     print(type(local))
#------------------------



