import time
import configparser
import requests
import urllib3.exceptions
from requests.auth import AuthBase
import datetime
import json
from pymongo import MongoClient
import psycopg2
from sys import exit

# config parser
config = configparser.ConfigParser()
config.read('conf.ini')
consumer_key = config['Twitter']['consumer_key']
consumer_secret = config['Twitter']['consumer_secret']
logfile = config['Logfile']['path']
tweetaccounts = config['Twitter']['accounts']
tweetcount = config['Twitter']['tweetcount']
pghost = config['Postgres']['host']
pguser = config['Postgres']['user']
pgpass = config['Postgres']['password']
pgdb = config['Postgres']['db']
mongohost = config['Mongo']['server']
mongouser = config['Mongo']['user']
mongopass = config['Mongo']['pass']
mongodb = config['Mongo']['db']
mongocoll = config['Mongo']['collection']


# Gets a bearer token
class BearerTokenAuth(AuthBase):
    def __init__(self, consumer_key, consumer_secret):
        self.bearer_token_url = "https://api.twitter.com/oauth2/token"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.bearer_token = self.get_bearer_token()

    def get_bearer_token(self):
        response = requests.post(
            self.bearer_token_url,
            auth=(self.consumer_key, self.consumer_secret),
            data={'grant_type': 'client_credentials'},
            headers={'User-Agent': 'TwitterDevFilteredStreamQuickStartPython'})

        if response.status_code != 200:
            raise Exception(f"Cannot get a Bearer token (HTTP %d): %s" % (response.status_code, response.text))

        body = response.json()
        return body['access_token']

    def __call__(self, r):
        r.headers['Authorization'] = f"Bearer %s" % self.bearer_token
        r.headers['User-Agent'] = 'TwitterDevFilteredStreamQuickStartPython'
        return r


bearer_token = BearerTokenAuth(consumer_key, consumer_secret)
tweetList0 = tweetaccounts.splitlines()
tweetList = [item for item in tweetList0 if item]
dt_now = datetime.datetime.now()
runNum = 0



if __name__ == "__main__":
    for account in tweetList:
        lf = open(logfile, 'a')
        try:
            client = MongoClient(host=mongohost, username=mongouser, password=mongopass)
        except Exception as e:
            exit("Unable to connect to mongo database!")
            lf.write("MONGO Error: ", str(e))
            lf.write('\n')
        db = client[mongodb]
        collection = db[mongocoll]
        try:
            conn = psycopg2.connect(f"dbname={pgdb} user={pguser} password={pgpass} host={pghost}")
        except Exception as e:
            exit("Unable to connect to postgres database!")
            lf.write("POSTGRES Error: ", str(e))
            lf.write('\n')
        cur = conn.cursor()
        cur.execute(f"SELECT twid FROM twitter WHERE acctid = '{account}' ORDER BY created DESC LIMIT 1;")
        lastTweet0 = cur.fetchone()
        lastTweet = None
        if lastTweet0:
            lastTweet = int(lastTweet0[0])
        dt_now_str2 = dt_now.strftime('%Y%m%d%H%M')
        #print(f"Account: {account}, Starting run: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lf.write(f"Starting Run, {account}, {str(runNum)}, {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        url2 = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={}&count={}".format(account,
                                                                                                        int(tweetcount))
        if lastTweet:
            url2 = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={}&count={}&since_id={}".format(
                account, int(tweetcount), lastTweet)
        try:
            response = requests.get(url2, auth=bearer_token)
        except urllib3.exceptions.MaxRetryError as e:
            print(f"ERROR: {str(e)}")
            print("Sleeping another 5 minutes before proceeding...")
            lf.write(account + ", " + "MaxRetryError: " + str(e) + '\n')
            lf.write(f"{account}, Sleeping another 5 minutes before proceeding..." + "\n")
            time.sleep(300)
            response = requests.get(url2, auth=bearer_token)
            if response.status_code == 200:
                print(f"{account} RECOVERED, connection successful")
                lf.write(f"{account} RECOVERED, connection successful" + "\n")
            else:
                print("UNABLE TO RECOVER!")
                lf.write("UNABLE TO RECOVER!" + "\n")
        if response.status_code != 200:
            lf.write(account + ", " + "httperr: " + str(response.status_code) + '\n')
        res = response.json()

        for item in list(reversed(res)):
            created = item["created_at"]
            format = "%a %b %d %X +0000 %Y"
            cts = datetime.datetime.strptime(created, format).isoformat()
            inserted = datetime.datetime.now().isoformat()
            item.update({"insertedTs": inserted})
            item.update({"createdTs": cts})
            hashtags, symbols = list(), list()
            if len(item['entities']['hashtags']) > 0:
                hashtags = [x['text'] for x in item['entities']['hashtags']]
            item.update({"hashtags": ",".join(hashtags)})
            if len(item['entities']['symbols']) > 0:
                # pull out symbols and add to a list
                symbols = [x["text"] for x in item['entities']['symbols']]
            item.update({"symbols": ",".join(symbols)})
            turl = item['entities']['urls'][0]['expanded_url'] if item['entities']['urls'] else ""
            cur.execute("""INSERT INTO twitter 
                            (twid, ttext, retweets, accname, url, created, inserted, hashtags, symbols, acctid, tjson) 
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (twid) DO NOTHING""",
                        (item['id_str'], item['text'], item['retweet_count'], item['user']['name'],
                         turl, item['createdTs'], item['insertedTs'],
                         item['hashtags'], item['symbols'], account, json.dumps(item)))
            collection.insert_one(item)
        conn.commit()
        cur.close()
        conn.close()
        lf.write(f"Finished {account} at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lf.close()
    runNum += 1
    #print(
    #    f"{datetime.datetime.now().isoformat(timespec='seconds')} -- Finished Run: {runNum}, sleeping for 5 minutes before retrieving new tweets...")


