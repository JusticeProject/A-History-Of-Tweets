import platform
import os
import os.path
import pathlib
import datetime
import re
import jinja2
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import brotlicffi
import time

import Classes

CONFIG_FILE_NAME = "../config/Config.txt"
CUSTOMIZED_HANDLES_FILE_NAME = "../config/CustomizedTwitterHandles.txt"
LIST_OF_CONGRESS_MEMBERS_FILENAME = "../output/ListOfCongressMembers.txt"
TWITTER_USERS_FROM_LISTS_FILENAME = "../output/TwitterUsersFromTwitterLists.txt"
USER_LOOKUP_FILENAME = "../output/UserLookup.txt"
DEFAULT_LOG_FOLDER = "../output/logs/"
KEYWORDS_FILE_NAME = "../config/Keywords.txt"
TEMPLATE_HTML_FILE_NAME = "template.html"
TEMPLATE_INDEX_RESULTS_FILE_NAME = "template-index-of-results.html"

CUSTOM_HTTP_HEADER_WIN10 = {
    "Sec-Ch-Ua":'Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
    "Device-Memory":"8",
    "Sec-Ch-Ua-Model":'',
    "Rtt":"50",
    "Sec-Ch-Ua-Mobile":"?0",
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Sec-Ch-Ua-Arch":'"x86"',
    "Viewport-Width":"1536",
    "Sec-Ch-Ua-Full-Version":'"96.0.4664.45"',
    "Sec-Ch-Ua-Platform-Version":'"10.0.0"',
    "Dpr":"1.25",
    "Downlink":"10",
    "Ect":"4g",
    "Sec-Ch-Prefers-Color-Scheme":"light",
    "Sec-Ch-Ua-Platform":'"Windows"',
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Sec-Fetch-Site":"none",
    "Sec-Fetch-Mode":"navigate",
    "Sec-Fetch-Dest":"document",
    "Accept-Encoding":"gzip, deflate, br",
    "Accept-Language":"en-US,en;q=0.9",
    "Sec-Fetch-User":"?1",
    "Upgrade-Insecure-Requests":"1"
}

CUSTOM_HTTP_HEADER_WIN7 = {
    "Sec-Ch-Ua":'" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
    "Device-Memory":"4",
    "Sec-Ch-Ua-Model":'',
    "Rtt":"50",
    "Sec-Ch-Ua-Mobile":"?0",
    "User-Agent":"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Sec-Ch-Ua-Arch":'"x86"',
    "Viewport-Width":"1600",
    "Sec-Ch-Ua-Full-Version":'"96.0.4664.45"',
    "Sec-Ch-Ua-Platform-Version":'"0.0.0"',
    "Dpr":"1",
    "Downlink":"4.15",
    "Ect":"4g",
    "Sec-Ch-Prefers-Color-Scheme":"light",
    "Sec-Ch-Ua-Platform":'"Windows"',
    "Accept":"application/signed-exchange;v=b3;q=0.7,*/*;q=0.8",
    "Sec-Fetch-Site":"none",
    "Sec-Fetch-Mode":"navigate",
    "Sec-Fetch-Dest":"document",
    "Accept-Encoding":"gzip, deflate, br",
    "Accept-Language":"en-US,en;q=0.9",
    "Sec-Fetch-User":"?1",
    "Upgrade-Insecure-Requests":"1"
}

CUSTOM_HTTP_HEADER_IPHONE = {
    "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding":"gzip, deflate, br",
    "Accept-Language":"en-US,en;q=0.9",
    "Referer":"https://www.google.com/"
}

###############################################################################
###############################################################################

def getCustomHeader(currentPlatform = True):
    if (currentPlatform):
        if ("Windows-10" in platform.platform()):
            return CUSTOM_HTTP_HEADER_WIN10
        else:
            return CUSTOM_HTTP_HEADER_WIN7
    else:
        return CUSTOM_HTTP_HEADER_IPHONE

###############################################################################
###############################################################################

def loadCredentials():
    cred = Classes.Credentials()
    configLines = open(CONFIG_FILE_NAME, "r").readlines()
    for line in configLines:
        cred.setData(line)
    
    return cred

###############################################################################
###############################################################################

def getCustomizedTwitterHandles():
    listOfExcludes = []
    listOfIncludes = []
    listOfSamePersons = []
    
    lines = open(CUSTOMIZED_HANDLES_FILE_NAME, "r").readlines()
    for line in lines:
        if ("exclude=@" in line):
            handle = line.split("@")[1]
            handle = handle.strip().lower()
            listOfExcludes.append(handle)
        elif ("include=@" in line):
            handle = line.split("@")[1]
            handle = handle.strip().lower()
            listOfIncludes.append(handle)
        elif ("same_person=" in line):
            line_split = line.split("@")
            handle1 = line_split[1].replace(",", "").strip().lower()
            handle2 = line_split[2].strip().lower()
            listOfSamePersons.append((handle1, handle2))
    
    return listOfExcludes,listOfIncludes,listOfSamePersons

###############################################################################
###############################################################################

# write the given list of data to a file

def saveCongressMembers(listOfMembers):
    listFile = open(LIST_OF_CONGRESS_MEMBERS_FILENAME, "w", encoding="utf-8")
    for member in listOfMembers:
        listFile.write(str(member) + "\n")
    listFile.close()
    
    logMessage = "data written to file " + LIST_OF_CONGRESS_MEMBERS_FILENAME
    return logMessage

###############################################################################
###############################################################################

def loadCongressMembers():
    listOfMembers = []
    listFileLines = open(LIST_OF_CONGRESS_MEMBERS_FILENAME, "r", encoding="utf-8").readlines()
    for line in listFileLines:
        member = Classes.CongressMember()
        member.setData(line)
        listOfMembers.append(member)
    
    return listOfMembers

###############################################################################
###############################################################################

def isCongressListAvailable():
    if (os.path.exists(LIST_OF_CONGRESS_MEMBERS_FILENAME) == False):
        return False
    
    if (os.path.exists(TWITTER_USERS_FROM_LISTS_FILENAME) == False):
        return False
    
    return True

###############################################################################
###############################################################################

def loadTwitterUsers():
    dictOfTwitterUsers = {}
    twitterHandlesLines = open(TWITTER_USERS_FROM_LISTS_FILENAME, "r", encoding="utf-8").readlines()
    for line in twitterHandlesLines:
        user = Classes.TwitterUser()
        user.setData(line)
        dictOfTwitterUsers[user.twitterHandle] = user
    
    return dictOfTwitterUsers

###############################################################################
###############################################################################

def saveTwitterUsers(dictOfTwitterUsers):
    if (os.path.exists("../output/") == False):
        os.mkdir("../output/")
    
    listFile = open(TWITTER_USERS_FROM_LISTS_FILENAME, "w", encoding="utf-8")
    for handle in dictOfTwitterUsers.keys():
        listFile.write(str(dictOfTwitterUsers[handle]) + "\n")
    listFile.close()

    logMessage = "data written to file " + TWITTER_USERS_FROM_LISTS_FILENAME
    return logMessage

###############################################################################
###############################################################################

# The UserLookup.txt file is used to connect each Twitter @handle to its user id number. 

def loadUserLookup():
    userLookupDict = {}
    
    file = open(USER_LOOKUP_FILENAME, "r", encoding="utf-8")
    lines = file.readlines()
    file.close()

    for line in lines:
        user = Classes.TwitterUser()
        user.setData(line)
        user.minimize()
        userLookupDict[user.twitterHandle] = user
            
    return userLookupDict

###############################################################################
###############################################################################

def saveUserLookup(userLookupDict):
    file = open(USER_LOOKUP_FILENAME, "w", encoding="utf-8")
    for handle in userLookupDict.keys():
        file.write(str(userLookupDict[handle]) + "\n")
    file.close()
    
    logMessage = "data written to file " + USER_LOOKUP_FILENAME
    return logMessage

###############################################################################
###############################################################################

def getISOTimeString(year, month, day, hour):
    then = datetime.datetime(year, month, day, hour)
    then = then.astimezone(datetime.timezone.utc)
    resultStr = then.isoformat(sep='T', timespec='seconds')
    resultStr = resultStr.split("+")[0] + "Z"
    return resultStr

###############################################################################
###############################################################################

def getPastTimeString(daysAgo=1):
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = datetime.timedelta(days=-daysAgo)
    result = now + delta
    resultStr = result.isoformat(sep='T', timespec='seconds')
    resultStr = resultStr.split("+")[0] + "Z"
    return resultStr

###############################################################################
###############################################################################

def getLocalTime():
    local = time.localtime()
    resultStr = time.strftime("%a, %d %b %Y %H:%M:%S", local)
    return resultStr

###############################################################################
###############################################################################

def getCurrentDate():
    now = datetime.datetime.now()
    resultStr = now.strftime("%Y-%m-%d-%a")
    return resultStr

###############################################################################
###############################################################################

def convertDateToReadable(date):
    dateObj = datetime.datetime.strptime(date, "%Y-%m-%d-%a")
    resultStr = dateObj.strftime("%a %B %d, %Y")
    return resultStr

###############################################################################
###############################################################################

def convertYearMonthToReadable(yearMonth):
    dateObj = datetime.datetime.strptime(yearMonth, "%Y-%m")
    resultStr = dateObj.strftime("%B %Y")
    return resultStr

###############################################################################
###############################################################################

def getWashingtonTime():
    # TODO: update Python and use the new timezone functionality
    now = datetime.datetime.now()
    delta = datetime.timedelta(hours=1)
    result = now + delta
    resultStr = result.strftime("%a %B %d, %Y at %I:%M %p Washington DC time.")
    return resultStr

###############################################################################
###############################################################################

def getCurrentHour():
    now = datetime.datetime.now()
    return now.hour

###############################################################################
###############################################################################

def saveTweets(listOfTweets, memberFolder, filename):
    RESULTS_FOLDER = "../output/" + memberFolder
    if (os.path.exists(RESULTS_FOLDER) == False):
        os.mkdir(RESULTS_FOLDER)
    
    TWEETS_FILENAME = RESULTS_FOLDER + "/" + filename + "-Tweets.txt"
    
    file = open(TWEETS_FILENAME, "w", encoding="utf-8")
    for tweet in listOfTweets:
        file.write(str(tweet) + "\n")
    file.close()
    
    return TWEETS_FILENAME

###############################################################################
###############################################################################

def getMostRecentResultsFolder():
    OUTPUT_FOLDER = "../output/"
    filesAndFolders = os.listdir(OUTPUT_FOLDER)
    filesAndFolders.sort(reverse=True)
    for item in filesAndFolders:
        if (item == "logs") or (item == "test"):
            continue
        
        p = pathlib.Path(OUTPUT_FOLDER + item)
        if p.is_dir():
            RESULTS_FOLDER = OUTPUT_FOLDER + item + "/"
            return RESULTS_FOLDER

###############################################################################
###############################################################################

def loadTweets(path):    
    listOfAllTweets = []

    fileLines = open(path, "r", encoding="utf-8").readlines()
    for line in fileLines:
        listOfAllTweets.append(line.strip())

    return listOfAllTweets

###############################################################################
###############################################################################

def saveURLs(dictOfURLs, memberFolder, filename):
    RESULTS_FOLDER = "../output/" + memberFolder
    if (os.path.exists(RESULTS_FOLDER) == False):
        os.mkdir(RESULTS_FOLDER)

    URLS_FILENAME = RESULTS_FOLDER + "/" + filename + "-URLs.txt"
    
    file = open(URLS_FILENAME, "w", encoding="utf-8")
    for shortened_url in dictOfURLs.keys():
        url_obj = dictOfURLs[shortened_url]
        file.write(str(url_obj) + "\n")
    file.close()

    return URLS_FILENAME

###############################################################################
###############################################################################

def loadURLs(path):
    dictOfURLs = {}

    fileLines = open(path, "r", encoding="utf-8").readlines()
    for line in fileLines:
        url_obj = Classes.URL()
        url_obj.setData(line.strip())
        key = url_obj.shortened_url
        dictOfURLs[key] = url_obj

    return dictOfURLs

###############################################################################
###############################################################################

def getKeywords():
    dictOfKeywords = {}
    
    # each word will start with 0 or 1 special characters [+_^~]
    # then have 1 or more non-special characters
    regex = re.compile(r"[+_^~]?[^+_^~]+")
    
    fileLines = open(KEYWORDS_FILE_NAME, "r", encoding="utf-8").readlines()
    
    currentCategory = ""
    for line in fileLines:
        lineStripped = line.strip()
        
        # we don't pay attention until we see the first category
        if ("Category=" in lineStripped):
            currentCategory = lineStripped.split("=")[1]
            dictOfKeywords[currentCategory] = []
        elif (len(currentCategory) > 0) and (len(lineStripped) > 0):
            if ("Keywords=" in lineStripped):
                lineStripped = lineStripped.split("=")[1]
            
            listOfWords = regex.findall(lineStripped)
            
            for i in range(0, len(listOfWords)):
                if (listOfWords[i][0] != '^'):
                    listOfWords[i] = listOfWords[i].lower()
                if (listOfWords[i][0] == '+'):
                    listOfWords[i] = listOfWords[i][1:]
                # make all single quotes standard, sometimes the funny single quotes appear
                if ("???" in listOfWords[i]) or ("??" in listOfWords[i]):
                    regexQuote = re.compile(r"[?????]")
                    listOfWords[i] = regexQuote.sub("'", listOfWords[i])
                
            dictOfKeywords[currentCategory].append(listOfWords)
            
    return dictOfKeywords

###############################################################################
###############################################################################

def getHTMLTemplate():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("../config/"))
    htmlTemplate = env.get_template(TEMPLATE_HTML_FILE_NAME)
    return htmlTemplate

###############################################################################
###############################################################################

def getHTMLTemplateIndexResults():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("../config/"))
    htmlTemplate = env.get_template(TEMPLATE_INDEX_RESULTS_FILE_NAME)
    return htmlTemplate

###############################################################################
###############################################################################

def saveHTMLResults(filename, html):
    OUTPUT_FILE_NAME = "../output/" + filename
    outputFile = open(OUTPUT_FILE_NAME, "w", encoding="utf-8")
    outputFile.write(html)
    outputFile.close()
    
    logMessage = "data written to file " + OUTPUT_FILE_NAME
    return logMessage, OUTPUT_FILE_NAME

###############################################################################
###############################################################################

def getDomainOfURL(url):
    if (url == ""):
        return ""

    domain = urlparse(url).netloc

    if (domain.startswith("www.")):
        domain = domain[4:]

    return domain

###############################################################################
###############################################################################

# helper function for retrieving all HTML data from a website

def getWebsiteHTML(url, currentPlatformHeaders = True):
    if (url == ""):
        return "", 0

    for retries in range(0, 3):
        try:
            custom_header = getCustomHeader(currentPlatformHeaders)
            result = requests.get(url, headers=custom_header, timeout=3)

            # TODO: the requests documentation says it should automatically decompress brotli encodings, but it wasn't doing that...
            if ("Content-Encoding" in result.headers.keys()) and (result.headers["Content-Encoding"] == "br"):
                decodedData = brotlicffi.decompress(result.content).decode() # decode from bytes to str
            else:
                decodedData = result.text
            
            result.close()
            return decodedData, result.status_code
        except:
            if (retries <= 1):
                time.sleep(1)

    return "", 1000

###############################################################################
###############################################################################

def getWebsiteFromGoogleCache(url, currentPlatformHeaders = True):
    return getWebsiteHTML("https://webcache.googleusercontent.com/search?q=cache:" + url, currentPlatformHeaders)

###############################################################################
###############################################################################

def extractTitleFromHTML(html):
    try:
        parsed_html = BeautifulSoup(html, 'html.parser')
    except:
        return ""

    if (parsed_html.title is not None) and (parsed_html.title.string is not None):
            title = parsed_html.title.string
            title = title.strip()
            title = title.replace("\n", "")
            title = title.replace("\r", "")
            return title
    
    return ""

###############################################################################
###############################################################################

class Logger:
    def __init__(self):
        self.filename = ""
        self.messages = []
        
    def prepareLogFile(self, logFolder=DEFAULT_LOG_FOLDER):
        # before starting a new log file, check if we still need to write any messages to the prev log
        if (self.filename != "") and (len(self.messages) > 0):
            self.flushLogs()

        if (os.path.exists(logFolder) == False):
            os.mkdir(logFolder)

        self.filename = logFolder + getCurrentDate() + "-log.txt"
        
    def log(self, text):
        print(text)
        
        if (self.filename == ""):
            return
        
        self.messages.append(text)
        if (len(self.messages) > 20):
            self.flushLogs()
        
    def flushLogs(self):
        for retries in range(0, 3):
            try:
                f = open(self.filename, "a", encoding="utf-8")
                for message in self.messages:
                    f.write(message + "\n")
                f.close()
                self.messages = []
                return
            except BaseException as e:
                strError = str(e.args)
                print("Error: problem flushing logs, someone might have the log file open")
                print(strError)
                time.sleep(10)
        
    def isErrorInLog(self):
        self.flushLogs()
        f = open(self.filename, "r", encoding="utf-8")
        data = f.read()
        f.close()
        if ("Error:" in data):
            return True
        else:
            return False
        
        