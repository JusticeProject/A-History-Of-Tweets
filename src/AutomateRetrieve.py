import time
import distutils.file_util
import os

import Utilities

import RetrieveTweets

###############################################################################
###############################################################################

SCAN_AFTER_HOUR = 14
SCAN_BEFORE_HOUR = 9
GOOGLE_DRIVE_LOGS = "C:/GoogleDrive/logs/"
GOOGLE_DRIVE_RESULTS = "C:/GoogleDrive/results/history/"

###############################################################################
###############################################################################

logger = Utilities.Logger()
listOfMembers = Utilities.loadCongressMembers()
listOfMembers.sort() # mix reps and sens together and sort them alphabetically

while len(listOfMembers) > 0:
    hour = Utilities.getCurrentHour()
    
    if (hour > SCAN_AFTER_HOUR) or (hour < SCAN_BEFORE_HOUR):
        member = listOfMembers.pop(0)
        memberFolder = member.last_name[0]

        logger.prepareLogFile(GOOGLE_DRIVE_LOGS + "history/" + memberFolder + "/")

        # retrieve the history of Tweets for this member of Congress
        step1 = RetrieveTweets.RetrieveTweets(logger)
        tweetsPath, urlsPath = step1.run(3, member)

         # make a backup of the raw tweet data in case we need to analyze it again
        destinationPath = GOOGLE_DRIVE_RESULTS + memberFolder + "/"
        if (os.path.exists(destinationPath) == False):
            os.mkdir(destinationPath)
        if (tweetsPath is not None):
            distutils.file_util.copy_file(tweetsPath, destinationPath)
            logger.log("copied " + tweetsPath + " to " + destinationPath)
        if (urlsPath is not None):
            distutils.file_util.copy_file(urlsPath, destinationPath)
            logger.log("copied " + urlsPath + " to " + destinationPath)
        
        logger.log("Done with member {}".format(member.last_name))

        logger.flushLogs()
        time.sleep(10 * 60)

    time.sleep(60)

print("Done!")
