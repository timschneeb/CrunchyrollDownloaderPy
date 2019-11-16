#!/usr/bin/python
import subprocess
import urllib.request
import requests, random, decimal, os
from datetime import datetime


class bcolor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def boolToColorStr(b):
    if b:
        return bcolor.OKGREEN + "true" + bcolor.ENDC
    else:
        return bcolor.FAIL + "false" + bcolor.ENDC

def getDeviceID():
    return ''.join(random.choice("abcdef1234567890") for i in range(32))

def getSession(useUSproxy):
    print("Requesting session id...")
    URL = ""
    if useUSproxy:
        URL = "https://api1.cr-unblocker.com/getsession.php?version=1.1"
    else:
        URL = "https://api.crunchyroll.com/start_session.1.json"

    PARAMS = {'device_id': getDeviceID(),
              'device_type': "com.crunchyroll.crunchyroid",
              'access_token': "Scwg9PRRZ19iVwD"}#"FLpcfZH4CbW4muO"}

    r = requests.post(url=URL, params=PARAMS)
    data = r.json()

    session = data['data']['session_id']
    country = data['data']['country_code']
    print(session)
    print(bcolor.OKBLUE + "Session ID received (" + country + ")" + bcolor.ENDC)
    return session

def prepareLoginForProxy(session,mail,passwd):
    print("Fetching auth token for proxy login...")
    URL = "https://api.crunchyroll.com/login.2.json"

    PARAMS = {'session_id': session,
              'account': mail,
              'password': passwd}

    r = requests.post(url=URL, params=PARAMS)
    data = r.json()
    print(bcolor.OKBLUE + "Auth token received" + bcolor.ENDC)
    return data['data']

def doLoginProxy(logindata):
    print("Logging in via proxy...")
    URL = "https://api2.cr-unblocker.com/start_session"

    PARAMS = {'version': '1.1',
              'auth': logindata['auth'],
              'user_id': logindata['user']['user_id']}

    r = requests.get(url=URL, params=PARAMS)
    data = r.json()

    username = data['data']['user']['username']
    premium = data['data']['user']['access_type']
    expires = data['data']['expires']
    datetime_obj = None
    try:
        datetime_obj = datetime.strptime(expires, "%Y-%m-%dT%H:%M:%S")
    except ValueError as v:
        if len(v.args) > 0 and v.args[0].startswith('unconverted data remains: '):
            line = expires[:-(len(v.args[0]) - 26)]
            datetime_obj = datetime.strptime(line, "%Y-%m-%dT%H:%M:%S")
        else:
            raise
    now = datetime.now()
    delta = datetime_obj - now
    new_expires = str(decimal.Decimal(round(delta.total_seconds()/60/60/24, 0)))

    print(bcolor.OKBLUE + "Logged in as " + username + " (" + premium + ")" + bcolor.ENDC)
    print("Account expiration date: " + datetime_obj.strftime("%Y-%m-%d %H:%M") + " (" + new_expires + " days)")
    return data['data']['session_id']

def doLogin(session,mail,passwd):
    print("Logging in...")
    URL = "https://api.crunchyroll.com/login.2.json"

    PARAMS = {'session_id': session,
              'account': mail,
              'password': passwd}

    r = requests.post(url=URL, params=PARAMS)
    data = r.json()

    username = data['data']['user']['username']
    premium = data['data']['user']['access_type']
    expires = data['data']['expires']
    datetime_obj = None
    try:
        datetime_obj = datetime.strptime(expires, "%Y-%m-%dT%H:%M:%S")
    except ValueError as v:
        if len(v.args) > 0 and v.args[0].startswith('unconverted data remains: '):
            line = expires[:-(len(v.args[0]) - 26)]
            datetime_obj = datetime.strptime(line, "%Y-%m-%dT%H:%M:%S")
        else:
            raise
    now = datetime.now()
    delta = datetime_obj - now
    new_expires = str(decimal.Decimal(round(delta.total_seconds()/60/60/24, 0)))

    print(bcolor.OKBLUE + "Logged in as " + username + " (" + premium + ")" + bcolor.ENDC)
    print("Account expiration date: " + datetime_obj.strftime("%Y-%m-%d %H:%M") + " (" + new_expires + " days)")

    for cookie in r.cookies:
        if cookie.name == "session_id":
            return cookie.value
    print(bcolor.FAIL + "Login failed" + bcolor.ENDC)
    return session

def searchPrompt():
    print()
    print(bcolor.BOLD + bcolor.HEADER + "Enter a search query:" + bcolor.ENDC)
    while True:
        selection = input(">")
        if len(selection) < 1:
            print(bcolor.FAIL + "Invalid input" + bcolor.ENDC)
            continue
        break
    return selection

def searchMedia(session,query):
    print("Searching for '" + query + "'...")
    URL = "https://api.crunchyroll.com/autocomplete.0.json"

    PARAMS = {'session_id': session,
              'q': query,
              'limit': '50',
              'offset': '0',
              'media_types': 'anime|drama'}

    r = requests.post(url=URL, params=PARAMS)
    data = r.json()
    try:
        results = data['data']
    except KeyError:
        results = {}

    if len(results) == 0:
        print(bcolor.FAIL + "No results found" + bcolor.ENDC)
        exit(1)
    elif len(results) == 1:
        print(bcolor.OKBLUE + "1 result found (" + results[0]['name'] +")" + bcolor.ENDC)
    else:
        print(bcolor.OKBLUE + str(len(results)) + " results found" + bcolor.ENDC)

    return results

def selectSearchResult(results):
    print()
    print(bcolor.BOLD + bcolor.HEADER + "Select a series [0-" + str(len(results)-1) + "]:" + bcolor.ENDC)
    i = 0
    for result in results:
        print("[" + str(i) + "] " + result['name'])
        i = i + 1
    while True:
        raw = input(">")
        try:
            selection = int(raw)
        except ValueError:
            print(bcolor.FAIL + "Invalid input" + bcolor.ENDC)
            continue

        if selection < 0 or selection >= len(results):
            print(bcolor.FAIL + "Input out of range" + bcolor.ENDC)
            continue
        break

    return results[selection]

def getCollections(session,locale,seriesid):
    URL = "https://api.crunchyroll.com/list_collections.0.json"

    PARAMS = {'session_id': session,
              'series_id': seriesid,
              'sort': 'asc',
              'locale': locale,
              'fields': 'collections.collection_id,collections.series_id,collections.name,'
                        'collections.series_name,collections.description,collections.media_type,'
                        'collections.season,collections.complete,collections.landscape_image,'
                        'collections.portrait_image,collections.availability_notes,collections.media_count,'
                        'collections.premium_only,collections.created,collections.mature'}

    r = requests.post(url=URL, params=PARAMS)
    data = r.json()
    try:
        collections = data['data']
    except KeyError:
        print(data)
        collections = {}

    if len(collections) == 0:
        print(bcolor.FAIL + "No collections found" + bcolor.ENDC)
        exit(1)
    else:
        print(bcolor.OKBLUE + str(len(collections)) + " collection(s) found" + bcolor.ENDC)

    return collections

def selectCollection(collections):
    print()
    print(bcolor.BOLD + bcolor.HEADER + "Select a collection [0-" + str(len(collections)-1) + "] or 'A' to select all:" + bcolor.ENDC)
    i = 0
    for collection in collections:
        print("[" + str(i) + "] " + collection['name'] + " (Season " + collection['season'] + ")")
        i = i + 1

    while True:
        raw = input(">")

        if raw.upper() == "A":
            return None

        try:
            selection = int(raw)
        except ValueError:
            print(bcolor.FAIL + "Invalid input" + bcolor.ENDC)
            continue
        selection = int(raw)
        if selection < 0 or selection >= len(collections):
            print(bcolor.FAIL + "Input out of range" + bcolor.ENDC)
            continue
        break

    return collections[selection]

def getEpisodes(session,locale,getAllCollections,collectionid):
    URL = "https://api.crunchyroll.com/list_media.0.json"
    PARAMS = {}

    if getAllCollections:
        PARAMS = {'session_id': session,
                  'series_id': collectionid,
                  'sort': 'asc',
                  'offset': '0',
                  'limit': '5000',
                  'locale': locale,
                  'fields': 'media.collection_name,media.media_id,'
                            'media.name,media.episode_number'}
    else:
        PARAMS = {'session_id': session,
                  'collection_id': collectionid,
                  'sort': 'asc',
                  'offset': '0',
                  'limit': '5000',
                  'locale': locale,
                  'fields': 'media.collection_name,media.media_id,'
                            'media.name,media.episode_number'}

    r = requests.post(url=URL, params=PARAMS)
    data = r.json()
    try:
        episodes = data['data']
    except KeyError:
        print(data)
        episodes = {}

    if len(episodes) == 0:
        print(bcolor.FAIL + "No episodes found" + bcolor.ENDC)
        exit(1)
    else:
        print(bcolor.OKBLUE + str(len(episodes)) + " episode(s) found" + bcolor.ENDC)

    return episodes


def printEpisodeDetails(episode,locale):
    collection = episode['collection_name']
    number = episode['episode_number']
    title = episode['name']
    available = episode['available']
    premium_only = episode['premium_only']
    hardsub_lang = episode['stream_data']['hardsub_lang']
    audio_lang = episode['stream_data']['audio_lang']
    format = episode['stream_data']['format']
    strbuilder = ""
    expires = ""

    for stream in episode['stream_data']['streams']:
        try:
            datetime_obj = datetime.strptime(stream['expires'], "%Y-%m-%dT%H:%M:%S")
        except ValueError as v:
            if len(v.args) > 0 and v.args[0].startswith('unconverted data remains: '):
                line = stream['expires'][:-(len(v.args[0]) - 26)]
                datetime_obj = datetime.strptime(line, "%Y-%m-%dT%H:%M:%S")
            else:
                raise
        now = datetime.now()
        delta = datetime_obj - now
        strbuilder += str(stream["quality"]).capitalize() + "; "
        expires = str(decimal.Decimal(round(delta.total_seconds()/60/60, 1)).normalize())

    print()
    print(bcolor.BOLD + "#" + number + " - " + title + bcolor.ENDC + " (" + collection + ")")
    print("Available: " + boolToColorStr(available) + ", Premium only: " + boolToColorStr(premium_only) + ", ")
    if len(episode['stream_data']['streams']) < 1:
        print(bcolor.FAIL + "Either this episode is premium or not available in the selected locale (" + locale + ")"
              + bcolor.ENDC)
    else:
        print("Audio: " + str(audio_lang) + ", Subtitle: " + str(hardsub_lang) + ", Format: " + str(format))
        print("Available qualities: " + strbuilder + "(Expires in " + expires + " hours)")


def getEpisode(session,locale,mediaid):
    URL = "https://api.crunchyroll.com/info.0.json"

    PARAMS = {'fields': 'media.collection_id,media.collection_name,'
                        'media.stream_data,media.available,media.episode_number,'
                        'media.series_name,media.premium_only,media.name',
              'session_id': session,
              'locale': locale,
              'media_id': mediaid
              }

    r = requests.post(url=URL, params=PARAMS)
    data = r.json()
    try:
        episode = data['data']
    except KeyError:
        try:
            print(bcolor.FAIL + "Unable to parse episode details: " + bcolor.ENDC + data['message'])
        except KeyError:
            print(bcolor.FAIL + "Unable to parse episode details " + bcolor.ENDC)
        finally:
            exit(1)

    return episode


def processEpisode(episode):
    collection = episode['collection_name']
    number = episode['episode_number']
    title = episode['name']
    series = episode['series_name']

    dir = series + "/" + collection + "/"
    if not os.path.exists(dir):
        os.makedirs(dir)

    i = 0
    adaptiveFound = False
    for stream in episode['stream_data']['streams']:
        quality = stream["quality"]
        if quality == "adaptive":
            adaptiveFound = True
            i += 1
            url = stream['url']
            urllib.request.urlretrieve(url, dir + series + " e" + number + " - " + title + ".m3u8")

    if not adaptiveFound:
        for stream in episode['stream_data']['streams']:
            quality = stream["quality"]
            url = stream['url']
            urllib.request.urlretrieve(url, dir + series + " e" + number + " - " + title + " (" + quality + ").m3u8")
            i += 1

    if i == 0:
        print(bcolor.FAIL + "No downloads available, skipping..." + bcolor.ENDC)
    else:
        print(bcolor.OKBLUE + str(i) + " file(s) have been downloaded." + bcolor.ENDC)

def listLocales():
    URL = "https://api.crunchyroll.com/list_locales.1.json"

    PARAMS = {'device_type': 'com.crunchyroll.crunchyroid',
              'access_token': 'Scwg9PRRZ19iVwD',
              'locale': '',
              'device_id': getDeviceID(),
              'version': '453'
              }

    r = requests.get(url=URL, params=PARAMS)
    data = r.json()
    print(bcolor.BOLD + bcolor.HEADER + "Available locales:" + bcolor.ENDC)
    try:
        locales = data['data']['locales']
        active = data['data']['active_locale']
        for locale in locales:
            print(bcolor.BOLD + locale['locale_id'] + bcolor.ENDC + " -> " + locale['label'])
        print("Default: " + active)
        print()
    except KeyError:
        try:
            print(bcolor.FAIL + "Unable to list locales: " + bcolor.ENDC + data['message'])
        except KeyError:
            print(bcolor.FAIL + "Unable to list locales" + bcolor.ENDC)
        finally:
            exit(1)

def downloadVideoURL(url,file,overwrite):
    try:
        executable = "ffmpeg"
        if os.name == 'nt':
            executable = "ffmpeg.exe"
        cmds = [executable, '-i', url, '-bsf:a', 'aac_adtstoasc', '-c', 'copy',
                '-stats', '-v', 'quiet', file]
        if overwrite:
            cmds.append('-y')

        subprocess.Popen(cmds)

    except KeyboardInterrupt:
        print(bcolor.FAIL + bcolor.BOLD + "Keyboard Interrupt: removing partial download..." + bcolor.ENDC)
        if os.path.exists(file):
            os.remove(file)
        exit(0)
