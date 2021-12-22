import tweepy
import Utilities
import Classes

import time

###############################################################################
###############################################################################

class RetrieveTweets:
    def __init__(self, logger):
        self.logger = logger
            
    ###########################################################################
    ###########################################################################

    def copyTweetData(self, rawTweet, isRefTweet):
        tweet = Classes.Tweet()
        tweet.id = rawTweet.id
        tweet.author_id = rawTweet.author_id
    
        # convert the datetime object from UTC to local time, then to a string
        timestamp = rawTweet.created_at.astimezone()
        tweet.created_at = timestamp.strftime("%m/%d/%Y")
    
        tweet.conversation_id = rawTweet.conversation_id
        tweet.in_reply_to_user_id = rawTweet.in_reply_to_user_id
        tweet.is_ref_tweet = isRefTweet
    
        # convert list of dicts to just a list for referenced tweets
        if (rawTweet.referenced_tweets is not None):
            tweet.list_of_referenced_tweets = []
            for refTweet in rawTweet.referenced_tweets:
                tweet.list_of_referenced_tweets.append(refTweet["type"])
                tweet.list_of_referenced_tweets.append(int(refTweet["id"]))
        else:
            tweet.list_of_referenced_tweets = None
    
        # grab the list of media keys, we will get the media later
        if (rawTweet.attachments is not None) and ("media_keys" in rawTweet.attachments.keys()):
            tweet.list_of_attachments = rawTweet.attachments["media_keys"]
        else:
            tweet.list_of_attachments = None

        # grab the urls if there are any
        urls = {}
        if (rawTweet.entities is not None) and ("urls" in rawTweet.entities.keys()):
            for item in rawTweet.entities["urls"]:
                shortened_url = item["url"]

                # store the shortened url in the Tweet object
                if (shortened_url not in tweet.list_of_urls):
                    tweet.list_of_urls.append(shortened_url)

                # store the shortened url plus the expanded info in URL object, these will be kept in a separate file
                if (shortened_url not in urls):
                    url_obj = Classes.URL()
                    url_obj.shortened_url = shortened_url
                    url_obj.expanded_url = item["expanded_url"]
                    if ("title" in item.keys()):
                        url_obj.title = item["title"]
                    urls[shortened_url] = url_obj

        tweet.text = rawTweet.text
        
        return tweet, urls

    ###########################################################################
    ###########################################################################

    def replaceMediaKeysWithData(self, listOfTweets, listOfMedia):
        for tweet in listOfTweets:
            if (tweet.list_of_attachments is None):
                continue
            
            newAttachmentsList = []
            
            for media_key in tweet.list_of_attachments:
                for mediaObject in listOfMedia:
                    if (media_key == mediaObject.media_key):
                        newAttachmentsList.append(mediaObject.data["type"])
                        if ("url" in mediaObject.data.keys()):
                            newAttachmentsList.append(mediaObject.data["url"])
                        else:
                            newAttachmentsList.append("")
    
            tweet.list_of_attachments = newAttachmentsList
            
        return

    ###########################################################################
    ###########################################################################

    def retrieveTweetsForUser(self, user, startTime, endTime, secsBetweenRequests):
        tweet_fields_list = ["id",
                             "text",
                             "author_id",
                             "created_at",
                             "conversation_id",
                             "in_reply_to_user_id",
                             "referenced_tweets",
                             "attachments",
                             "entities"]
        expansions_list = ["referenced_tweets.id", "attachments.media_keys"]
        media_fields_list = ["media_key","type","url"]
    
        cred = Utilities.loadCredentials()
        client = tweepy.Client(cred.Bearer_Token)
        
        self.logger.log("retrieving tweets for handle " + user.twitterHandle + " start_time=" + startTime)
        responses = tweepy.Paginator(client.get_users_tweets, user.idStr, 
                                        start_time=startTime,
                                        end_time=endTime,
                                        max_results=100, # per page
                                        tweet_fields=tweet_fields_list,
                                        media_fields=media_fields_list,
                                        expansions=expansions_list)
    
        tweets = []
        dictOfUrls = {}
        listOfMedia = []
    
        for response in responses:
            
            if (response.data is None):
                continue
            
            # get the tweets in the data, the oldest tweet will always be in the front of the list
            for rawTweet in response.data:
                tweet, urls = self.copyTweetData(rawTweet, False)
                tweets.insert(0, tweet)
                dictOfUrls.update(urls)
                
            # get the tweets in the includes which detail the referenced tweets, if there are any,
            # these will always be at the back of the list
            if "tweets" in response.includes.keys():
                for rawTweet in response.includes["tweets"]:
                    tweet, urls = self.copyTweetData(rawTweet, True)
                    tweets.append(tweet)
                    dictOfUrls.update(urls)
    
            # grab the media keys if there are any
            if "media" in response.includes.keys():
                listOfMedia = listOfMedia + response.includes["media"]

            time.sleep(secsBetweenRequests)
    
        # replace the media keys with the actual data
        self.replaceMediaKeysWithData(tweets, listOfMedia)
        
        self.logger.log("received " + str(len(tweets)) + " for handle " + user.twitterHandle)
        return tweets, dictOfUrls
    
    ###########################################################################
    ###########################################################################
    
    def run(self, secsBetweenRequests, member):
        startTime = Utilities.getPastTimeString(10 * 365)
        endTime = Utilities.getISOTimeString(2021, 10, 21, 14)
        userLookupDict = Utilities.loadUserLookup()
    
        tweetsToSave = []
        urlsToSave = {}
        filename = member.last_name
        for handle in member.twitter:
            if (handle == ""):
                continue

            filename += "-" + handle
            
            user = userLookupDict[handle]
                
            while True:
                try:
                    newTweets, urls = self.retrieveTweetsForUser(user, startTime, endTime, secsBetweenRequests)
                    tweetsToSave = tweetsToSave + newTweets
                    urlsToSave.update(urls)
                    break
                except BaseException as e:
                    self.logger.log("Warning: failed to retrieve tweets for handle " + handle)
                    self.logger.log(str(e.args))
                    time.sleep(2 * 60)
                

        if (len(tweetsToSave) == 0):
            self.logger.log("No tweets retrieved for member {}".format(member.last_name))
            return None, None

        tweetsToSave.sort()

        self.logger.log("saving " + str(len(tweetsToSave)) + " tweets")
        memberFolder = member.last_name[0]
        tweetsPath = Utilities.saveTweets(tweetsToSave, memberFolder, filename)
        self.logger.log("Tweets saved to {}".format(tweetsPath))

        # save the urls
        self.logger.log("Saving {} urls".format(len(urlsToSave)))
        urlsPath = Utilities.saveURLs(urlsToSave, memberFolder, filename)
        self.logger.log("Urls saved to {}".format(urlsPath))
        
        return tweetsPath, urlsPath

###############################################################################
###############################################################################

if __name__ == "__main__":
    logger = Utilities.Logger()
    logger.prepareLogFile()
    # TODO:
    instance = RetrieveTweets(logger)
    instance.run(2, 2)
    
