# Twitter Scroller Project

## Install
- pip install -r requirements.txt
- in twitter-gather.py, line 14, enter absolute path to conf.ini so cron can find config file
## 1) Gather Tweets, put into database
set twitter-gather.py to run in a cron job every 5 minutes:
>*/5 * * * * /path/to/twitter-gather.py
## 2) Run scroller
localhost:8000/twitter/scroller
#### Currently running via Django's development server
from companalysis/ directory:
>python manage.py runserver 0.0.0.0:8000
> 
use command above to run on all interfaces/IPs on port 8000
## Description: 

1) A backend to pull tweets from Twitter and insert into Postgres and Mongo
- conf.ini contains config info for the Twitter api, Postgres, and Mongo
- conf.ini also contains twitter accounts to pull, number of tweets to pull, interval to pull at, and other configurations
- twitter-gather.py pulls and inserts tweets into Postgres and Mongo
- if desired, comment out Mongo sections as it's presently not used

2) Django frontend to display the tweet stream 
- the Django companalysis project contains the Django app twitter
- the app contains (so far) two pages, a feeds page that lists that feeds (pulled from postgres)
- the scroller page scrolls through the tweets via javascript

