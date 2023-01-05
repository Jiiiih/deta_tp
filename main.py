from flask import redirect, url_for, Flask, render_template, request
from markupsafe import escape
import requests
# for tp3
from pytrends.request import TrendReq
import pandas as pd
# for tp2
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime
import time
from functools import wraps
from collections import Counter

app = Flask(__name__)
app.config.from_pyfile('settings.py')

flow = None

# defining functions
# function to get data from google trends
def get_data(keyword):
    # get trend of last 90 days
    keyword = [keyword]
    pytrend = TrendReq()
    pytrend.build_payload(kw_list=keyword)
    df = pytrend.interest_over_time()
    df.drop(columns=['isPartial'], inplace=True)
    df.reset_index(inplace=True)
    df.columns = ["ds", "y"]
    return df

# defining ga auth
def ga_auth(scopes):
    global flow
    auth_url = "/"
    try:
        flow = InstalledAppFlow.from_client_config(get_cred_dict(), scopes)
        print(get_cred_dict())
        flow.redirect_uri = 'https://5i6fy9.deta.dev/cookies'
        auth_url, _ = flow.authorization_url(prompt='consent')
        print('Go to this URL: {}'.format(auth_url))
    except Exception as e:
        print('exception')
        print(e)

    return '{}'.format(auth_url)


def get_cred_dict():
    credentials_dict = {
        "web": {
            "client_id": app.config.get("CLIENT_ID"),
            "project_id": app.config.get("PROJECT_ID"),
            "auth_uri": app.config.get("AUTH_URI"),
            "token_uri": app.config.get("TOKEN_URI"),
            "auth_provider_x509_cert_url": app.config.get("AUTH_PROVIDER_X509_CERT_URL"),
            "client_secret": app.config.get("CLIENT_SECRET")
        }
    }
    return credentials_dict


# decorator to log execution time
def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Execution time: {end_time - start_time} seconds")
        return result
    return wrapper


prefix_google = """
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-252992004-1"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'UA-252992004-1');
</script>

 """


@app.route('/', methods=["GET", "POST"])
def home():
    if request.method == 'POST':
        if request.form.get('action1') == 'LOGS':
            return prefix_google + render_template('logger.html')
        else:
            pass  # unknown
    elif request.method == 'GET':
        return prefix_google + render_template("home.html")

    return prefix_google + render_template("home.html")


@app.route('/logger', methods=["GET", "POST"])
def show_logs():
    print("log from python")
    return render_template("logger.html")


# @app.route('/seecookies', methods=["GET"])
# def show_cookies():
#         req = requests.get('https://www.google.com')
#         print(req.cookies.get_dict())
#         print("cookies from python")
#         return render_template("cookies.html")


@app.route('/ganalytics', methods=["GET"])
def ganalytics():
    req = requests.get(
        "https://analytics.google.com/analytics/web/#/report-home/a250996037w345084258p281218202")
    return req.text


@app.route('/cookies/oauth', methods=["GET"])
def oauth():
    # Set Scopes
    scopes = ['https://www.googleapis.com/auth/analytics.readonly']
    auth_url = ga_auth(scopes)
    return redirect(auth_url)


@app.route('/cookies/', methods=["GET"])
def cookies():
    try:
        code = request.args.get('code', None)
        print("code")
        print(code)
        # state = request.args.get('state', None)
        # flow.fetch_token(code)
        print("flow")
        print(flow.fetch_token(code=code))
        print("printed")
    except Exception as e:
        print('exception')
        print(e)
    return redirect(url_for('visitors'))


@app.route('/cookies/visitors', methods=["GET"])
def visitors():
    google_cookies = "Unable to get cookies"
    try:
        req = requests.get("https://www.google.com/")
        google_cookies = req.cookies.get_dict()
        google_cookies = str(json.dumps(google_cookies, indent=2))

        service = build('analytics', 'v3', credentials=flow.credentials)
        results = service.data().ga().get(
            ids='ga:' + app.config.get("VIEW_ID"),
            start_date='30daysAgo',
            end_date='today',
            metrics='ga:users'
        ).execute()
        number_users = results['totalsForAllResults']['ga:users']
    except Exception as e:
        print('exception')
        print(e)

    display = prefix_google + \
        render_template('gaauth.html', google_cookies=google_cookies,
                        number_users=str(number_users))

    return display


# # TP3
@app.route('/plot', methods=["GET"])
@log_execution_time
def plot():
    keyword_1 = "Bleach"
    keyword_2 = "Naruto"

    pytrends = TrendReq()
    pytrends.build_payload(
        kw_list=[keyword_1, keyword_2], timeframe='today 5-y', geo='FR')
    df = pytrends.interest_over_time()

    df_keyword_1 = df[keyword_1].tolist()
    df_keyword_2 = df[keyword_2].tolist()

    df_date = df.index.values.tolist()

    timestamp_in_seconds = [element/1e9 for element in df_date]
    date = [datetime.fromtimestamp(element) for element in timestamp_in_seconds]
    days = [element.date() for element in date]
    months = [element.isoformat() for element in days]

    params = {
        "type": 'line',
        "data": {
            "labels": months,
            "datasets": [{
                "label": keyword_1,
                "data": df_keyword_1,
                "borderColor": '#3e95cd',
                "fill": 'false',
            },
                {
                "label": keyword_2,
                "data": df_keyword_2,
                "borderColor": '#ffce56',
                    "fill": 'false',
            }
            ]
        },
        "options": {
            "title": {
                "text": 'Trend comparison'
            },
            "scales": {
                "yAxes": [{
                    "ticks": {
                          "beginAtZero": 'true'
                          }
                }]
            }
        }
    }

    prefix_chartjs = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.5.0/Chart.min.js"></script>
    <canvas id="myChart" width="1200px" height="700px"></canvas>""" + f"""
    <script>
    var ctx = document.getElementById('myChart');
    var myChart = new Chart(ctx, {params});
    </script>
    """
    return prefix_chartjs

@app.route('/shakespeare', methods=["GET"])
@log_execution_time
def counting_words_shakespeare():
    with open('shakespeare.txt', 'r') as f:
        text = f.read()

    word_counts = {}
    for word in text.split():
        if word in word_counts:
            word_counts[word] += 1
        else:
            word_counts[word] = 1
    
    return render_template('count.html', word_counts=word_counts)

@app.route('/shakespeare/second', methods=["GET"])
@log_execution_time
def counting_counter():
    with open('shakespeare.txt', 'r') as f:
        text = f.read()

    # Split the text into words
    words = text.split()

    # Use the Counter function to count the number of occurrences of each word
    word_counts = Counter(words)

    return render_template('count.html', word_counts=word_counts)




if __name__ == '__main__':
    app.debug = True
    app.run()
