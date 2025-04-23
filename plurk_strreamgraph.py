from datetime import datetime
import matplotlib.pyplot as plt
import sqlite3
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")

TIMELINE_LIMIT = 100  # how many plurks to retrieve per call

#   {"lang": "en", "posted": "Fri, 05 Jun 2009 23:07:13 GMT", "qualifier": "thinks", "plurk_id": 90812, "owner_id": 1, "content": "test me out", "user_id": 1, "is_unread": 1, "no_comments": 0, "plurk_type": 0}
PLURK_DDL = """
CREATE TABLE IF NOT EXISTS plurks (
    lang TEXT,
    posted TEXT,
    qualifier TEXT,
    plurk_id INTEGER PRIMARY KEY,
    owner_id INTEGER,
    content TEXT,
    user_id INTEGER,
    is_unread INTEGER,
    no_comments INTEGER,
    plurk_type INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

#  {"display_name": "amix3", "gender": 0, "nick_name": "amix", "has_profile_image": 1, "id": 1, "avatar": null}
USER_DDL = """
CREATE TABLE IF NOT EXISTS users (
    display_name TEXT,
    gender INTEGER,
    nick_name TEXT,
    has_profile_image INTEGER,
    id INTEGER PRIMARY KEY,
    avatar TEXT
);
"""

# [{'id': 634534091421664, 'user_id': 3121150, 'plurk_id': 353058601160878, 'qualifier': ':', 'posted': 'Sun, 20 Apr 2025 17:31:18 GMT', 'lang': 'ne', 'content': 'heeft zo lekker in de zon geroeid vanmiddag.', 'last_edited': None, 'coins': None, 'editability': 0, 'qualifier_translated': ''}, {'id': 634554389970039, 'user_id': 6217927, 'plurk_id': 353058601160878, 'qualifier': 'has', 'posted': 'Tue, 22 Apr 2025 13:34:20 GMT', 'lang': 'ne', 'content': 'lekker in het park gelegen!!<a href="https://flickr.com/photos/rhodes/54467286223" class="ex_link meta" rel="nofollow" target="_blank"><img src="https://live.staticflickr.com/65535/54467286223_22a1bae646_b.jpg" height="48px">Chillin @ Sugar House Park</a>', 'last_edited': None, 'coins': None, 'with_random_emos': False, 'editability': 0, 'qualifier_translated': 'heeft'}, {'id': 634554833844859, 'user_id': 3114739, 'plurk_id': 353058601160878, 'qualifier': 'says', 'posted': 'Tue, 22 Apr 2025 14:32:08 GMT', 'lang': 'ne', 'content': 'dat vandaag ook een ontzettend fijne dag is. Ben met B rondje Durgerdam/Zunderdorp gaan doen.', 'last_edited': None, 'coins': None, 'editability': 0, 'qualifier_translated': 'zegt'}]
REPLIES_DDL = """
CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    plurk_id INTEGER,
    qualifier TEXT,
    posted TEXT,
    lang TEXT,
    content TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plurk_id) REFERENCES plurks(plurk_id)
)
"""


def _get_db_conn():
    return sqlite3.connect("plurks.db")


def setup_sqlite() -> None:
    conn = _get_db_conn()
    conn.execute(PLURK_DDL)
    conn.execute(USER_DDL)
    conn.execute(REPLIES_DDL)
    conn.commit()


def get_consumer() -> OAuth1Session:
    """
    gets consumer session

    Returns:
        OAuth1Session: consumer
    """
    oauth = OAuth1Session(
        CONSUMER_KEY, client_secret=CONSUMER_SECRET, callback_uri="oob"
    )

    # Step 1: Get a Request Token
    request_token_url = "https://www.plurk.com/OAuth/request_token"
    fetch_response = oauth.fetch_request_token(request_token_url)
    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    print("Request Token:", resource_owner_key)
    print("Request Token Secret:", resource_owner_secret)

    # Step 2: Authorize the Request Token
    base_authorization_url = "https://www.plurk.com/OAuth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print("Please go here and authorize:", authorization_url)
    verifier = input("Enter the verification code provided by Plurk: ")

    # Step 3: Exchange the Request Token for an Access Token
    access_token_url = "https://www.plurk.com/OAuth/access_token"
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    tokens = oauth.fetch_access_token(access_token_url)
    consumer = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=tokens["oauth_token"],
        resource_owner_secret=tokens["oauth_token_secret"],
    )
    return consumer


def get_timeline(consumer: OAuth1Session, offset: datetime.timestamp = None) -> dict:
    """
    gets timeline from plurk api

    Args:
        consumer (OAuth1Session): consumer
        offset (datetime.timestamp, optional): offset. Defaults to None.

    Returns:
        dict: timeline

    """
    TIMELINE_URL = "https://www.plurk.com/APP/Timeline/getPlurks"

    params = {"minimal_data": "1", "limit": TIMELINE_LIMIT}
    if offset is not None:
        offset_str = datetime.fromtimestamp(float(offset)).isoformat()
        print(f"getting timeline with offset {offset_str}")
        params["offset"] = offset_str
    else:
        print("getting timeline without offset")

    response = consumer.request("GET", TIMELINE_URL, params=params)

    resp = response.json()
    plurks = resp["plurks"]
    users = resp["plurk_users"]

    for plurk in plurks:
        plurk["posted"] = datetime.strptime(
            plurk["posted"], "%a, %d %b %Y %H:%M:%S %Z"
        ).timestamp()
    return {"plurks": plurks, "plurk_users": users}


def get_replies(consumer: OAuth1Session, plurk_id: int):
    """
    gets replies from plurk api

    Args:
        consumer (OAuth1Session): consumer
        plurk_id (int): plurk id

    Returns:
        list: replies
    """
    RESPONSES_URL = "https://www.plurk.com/APP/Responses/get"
    response = consumer.request(
        "GET",
        RESPONSES_URL,
        params={"minimal_data": "1", "plurk_id": plurk_id},
    )
    replies = response.json()["responses"]
    for reply in replies:
        reply["posted"] = datetime.strptime(
            reply["posted"], "%a, %d %b %Y %H:%M:%S %Z"
        ).timestamp()
    return replies


def own_profile(consumer: OAuth1Session):
    """
    gets own profile from plurk api

    Args:
        consumer (OAuth1Session): consumer

    Returns:
        dict: own profile
    """
    OWN_PROFILE_URL = "https://www.plurk.com/APP/Profile/getOwnProfile"

    response = consumer.request(
        "GET",
        OWN_PROFILE_URL,
    )
    return response.json()
    # print(response.text)


def main():
    # setup db
    print("setting up db")
    setup_sqlite()

    # get consumer
    print("getting consumer")
    consumer = get_consumer()

    # get own profile - we're not using this
    print("getting own profile")
    my_profile = own_profile(consumer)

    conn = _get_db_conn()

    print("getting initial offset")
    posted_val = conn.execute("SELECT MIN(posted) FROM plurks").fetchone()[0]
    if posted_val is None:
        offset = None
    else:
        offset = float(posted_val)
    print(f"initial offset is {offset}")

    while True:
        print(f"getting timeline with offset {offset}")
        timeline = get_timeline(consumer, offset=offset)
        if len(timeline["plurks"]) == 0:
            print("no more plurks to get")
            break

        users = timeline["plurk_users"] or {}

        for user in users.values():
            conn.execute(
                """INSERT OR REPLACE INTO users VALUES
                (:display_name, :gender, :nick_name, :has_profile_image, :id, :avatar)""",
                user,
            )
        conn.commit()

        for plurk in timeline["plurks"]:
            conn.execute(
                """INSERT OR REPLACE INTO plurks VALUES
                (:lang, :posted, :qualifier, :plurk_id, :owner_id, :content, :user_id, :is_unread, :no_comments, :plurk_type)""",
                plurk,
            )
        conn.commit()

        for plurk in timeline["plurks"]:
            plurk_id = plurk["plurk_id"]
            plurk_replies = get_replies(consumer, plurk_id)
            # store in db
            for reply in plurk_replies:
                conn.execute(
                    """INSERT OR REPLACE INTO replies VALUES
                    (:id, :user_id, :plurk_id, :qualifier, :posted, :lang, :content)""",
                    reply,
                )
        conn.commit()

        # get number of plurks now in db
        plurks_count = conn.execute("SELECT COUNT(1) FROM plurks").fetchone()[0]
        users_count = conn.execute("SELECT COUNT(1) FROM users").fetchone()[0]
        replies_count = conn.execute("SELECT COUNT(1) FROM replies").fetchone()[0]
        # get oldest and newest plurk
        oldest_plurk = conn.execute("SELECT MIN(posted) FROM plurks").fetchone()[0]
        newest_plurk = conn.execute("SELECT MAX(posted) FROM plurks").fetchone()[0]

        offset = oldest_plurk

        print(f"timeline now contains {plurks_count} plurks")
        print(f"users now contains {users_count} users")
        print(f"replies now contains {replies_count} replies")
        print(f"oldest plurk is {oldest_plurk}")
        print(f"newest plurk is {newest_plurk}")
        # break


if __name__ == "__main__":
    main()
