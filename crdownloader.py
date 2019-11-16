#!/usr/bin/python

import sys, getopt
from core import *
from colorama import init

init()


def usage():
    print(bcolor.HEADER + bcolor.BOLD + 'crdownloader.py [options]' + bcolor.ENDC)
    print(bcolor.OKBLUE + '[Authentication]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-p', '--account=<mail:password>', 'Login using specified (premium) account;'
          ' email and password need to be separated by a colon'))
    print(bcolor.OKBLUE + '[Regional Settings]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-u', '--unblock', 'Bypass regional blocked content (use US proxy)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-l', '--locale=<locale>', 'Set desired locale; some content is only downloadable in some specific locales'))
    print('\t{:<2s}  {:<30s} {:<10s}'.format('-L', '--list-locales', 'View a list of all available locales'))
    print(bcolor.OKBLUE + '[Automation]' + bcolor.ENDC)
    print('\t{:<2s}  {:<30s} {:<10s}'.format('-q', '--query=<keywords>', 'Set a search query; the first result will be picked'))
    print('\t{:<2s}  {:<30s} {:<10s}'.format('-C', '--all-collections', 'Skip user interaction and download all collections/seasons'))
    print('\t{:<2s}  {:<30s} {:<10s}'.format('-m', '--only-m3u', 'Only download the M3U8 HLS playlists (fast)'))
    print(bcolor.OKBLUE + '[FFMPEG/Downloader]' + bcolor.ENDC)
    print('\t{:<2s}  {:<30s} {:<10s}'.format('-y', '--overwrite', 'Overwrite video file, if it already exists'))


def main(argv):
    useAccount = False
    useUSproxy = False
    locale = "enUS"
    searchQuery = ""
    allCollections = False
    m3uOnly = False
    overwrite = False
    # mail = "acontreras562@gmail.com"
    # pwd = "Steelers15"
    mail = ""
    pwd = ""

    try:
        opts, args = getopt.getopt(argv, "1huLyCml:p:q:", ["overwrite", "list-locales", "query=", "unblock", "locale=", "account=",
                                                          "only-m3u8"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-u", "--unblock"):
            useUSproxy = True
        elif opt in ("-L", "--list-locales"):
            listLocales()
            exit(1)
        elif opt in ("-l", "--locale"):
            locale = arg
        elif opt in ("-p", "--account"):
            parts = str(arg).split(":")
            if len(parts) == 2:
                mail = parts[0]
                pwd = parts[1]
                useAccount = True
            else:
                print(bcolor.FAIL + "Invalid account\n"
                                    "You need to join the email and password of the account seperated by a colon\n"
                                    "Example: --account=somemail@example.com:password123" + bcolor.ENDC)
                exit(1)
        elif opt in ("-q", "--query"):
            searchQuery = arg
        elif opt in ("-C", "--all-collections"):
            allCollections = True
        elif opt in ("-m", "--only-m3u8"):
            m3uOnly = True
        elif opt in ("-y", "--overwrite"):
            overwrite = True

    session = None
    if useUSproxy and useAccount:
        pre_session = getSession(useUSproxy)
        logindata = prepareLoginForProxy(pre_session, mail, pwd)
        session = doLoginProxy(logindata)
    else:
        session = getSession(useUSproxy)
        if useAccount: session = doLogin(session, mail, pwd)

    if searchQuery == "":
        searchQuery = searchPrompt()
        results = searchMedia(session, searchQuery)
        if len(results) > 1:
            result = selectSearchResult(results)
        elif len(results) == 1:
            result = results[0]
    else:
        results = searchMedia(session, searchQuery)
        result = results[0]

    collections = getCollections(session, locale, result['series_id'])
    collection = None
    if not allCollections:
        if len(collections) > 1:
            collection = selectCollection(collections)
        elif len(results) == 1:
            collection = collections[0]

    if collection is None:
        episodes = getEpisodes(session, locale, True, result['series_id'])
    else:
        episodes = getEpisodes(session, locale, False, collection['collection_id'])

    episodeList = []
    for meta_episode in episodes:
        episode = getEpisode(session, locale, meta_episode['media_id'])
        printEpisodeDetails(episode, locale)
        processEpisode(episode)
        episodeList.append(episode)

    print()
    print(bcolor.OKGREEN + "M3U8 HLS playlists have been downloaded" + bcolor.ENDC)
    if m3uOnly:
        exit(0)

    print(bcolor.HEADER + "Starting video download..." + bcolor.ENDC)
    for episode in episodeList:
        collection = episode['collection_name']
        number = episode['episode_number']
        title = episode['name']
        series = episode['series_name']
        print("Downloading " + bcolor.BOLD + "#" + number + " - " + title + bcolor.ENDC + " (" + collection + ")...")

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
                filename = dir + series + " e" + number + " - " + title + ".mp4"
                downloadVideoURL(url, filename,overwrite)

        if not adaptiveFound:
            for stream in episode['stream_data']['streams']:
                quality = stream["quality"]
                url = stream['url']
                filename = dir + series + " e" + number + " - " + title + " (" + quality + ").mp4"
                downloadVideoURL(url, filename,overwrite)
                i += 1
                break


if __name__ == "__main__":
    main(sys.argv[1:])
