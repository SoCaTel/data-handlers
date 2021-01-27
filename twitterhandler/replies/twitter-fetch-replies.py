#usr/bin/python
# encoding: utf-8

# -----------------------------------------------------------------------
# SoCaTel Twitter Feed
# twitter-fetch-replies
#  - fetches replies of tweets
# -----------------------------------------------------------------------

import json
import time
import redis
import tweepy
import os.path
import datetime
import requests
import coloredlogs, logging

logger = logging.getLogger('TWITTER_HANDLER')
coloredlogs.install(level='DEBUG', logger=logger)

# ----------------------------------------------------------------------
# TWITTER HELPER METHOD LIST
# ----------------------------------------------------------------------


def limit_exception_handling(api):
	"""
	Limit exception handling method is able to read the limit constraint from the api. This
	results to how many msec the API should not be used. A timer is then being used as a stalling 
	mechanism to stall the API from requesting data
	"""
	limit = api.rate_limit_status()
	logger.info('Error Twitter Limit Exception: ' + json.dumps(limit, indent=4, sort_keys=True))
	sleep_interval = limit['resources']["search"]["/search/tweets"]["reset"] - time.time()
	if sleep_interval > 0:
		logger.info('Sleeping for ' + str(sleep_interval) + 'msec')
		time.sleep(sleep_interval)


# -----------------------------------------------------------------------
# ELASTICSEARCH QUERY/UTILS METHOD LIST
# ------------------------------------------------------------------------


def qr_random_tweet(screen_name):
	"""
	Query returns a random tweet based on the screen_name parameter
	"""
	query = {
		"query": {
			"constant_score": {
				"filter": {
					"term": {
						"user.screen_name": screen_name
					}
				}
			}
		},
		"size": 1
	}
	return query


def qr_latest_reply_tweet(user_id):
	"""
	Query returns the latest reply on a descending order based on the id field
	"""
	query = {
		"query": {
			"constant_score": {
				"filter": {
					"term": {
						"in_reply_to_user_id": user_id
					}
				}
			}
		},
		"sort": [{
			"id": {
				"order": "desc"
			}
		}],
		"size": 1
	}
	return query


def twitter_bulk_save(data):
	"""
	Twitter bulk save prepares the data array that is required to be passed to the elastic's bulk insert REST API
	Preparation of bulk loading of twitter timeline data.
	First we create an index line just like the example shown below and
	then we add the dumped json string of the object
	{"index":{"_id":1}} 
	{"name":"John"} 
	"""
	to_return = ''
	for d in data:
		index = {'index': {'_id': d.id_str}}
		to_return = to_return + json.dumps(index) + '\n'
		to_return = to_return + json.dumps(d._json) + '\n'
	return to_return


def fetch_replies(api, elastic_endpoint, index_name, screen_name, count):
	"""
	Fetch Replies from Twitter per tweet
	"""
	logger.info("Fetching Replies initialization")
	logger.info("Performing a search request on elasticsearch to bring a random tweet for [" + screen_name + "]")
	search_path = elastic_endpoint + index_name + '/_search'
	query = qr_random_tweet(screen_name.lower())
	get_random_tweet = requests.get(search_path, json=query).json()

	if get_random_tweet['hits']['total']['value'] == 0:
		logger.warn("There are no existing tweets for [" + screen_name + ". Aborting operation for this account")
		return

	else:
		# Obtain user if from this random tweet
		user_id = get_random_tweet['hits']['hits'][0]['_source']['user']['id']
		logger.info("Twitter user id for [" + screen_name + "] is --> " + str(user_id))
		logger.info("Fetching tweet replies")

		# Initialisation of variables
		all_replies = []
		since_id = None
		max_id = None

		while True:
			# Performing a search request on elasticsearch to bring the total amount of replies/mentions we have so far
			logger.info(
				"Performing a search request on elasticsearch to bring the total amount of replies/mentions we have so far for " +
				screen_name)
			search_path = elastic_endpoint + index_name + '/_search'
			query = qr_latest_reply_tweet(user_id)
			resp = requests.get(search_path, json=query).json()

			if resp['hits']['total']['value'] != 0:
				logger.info('Existing replies/mentions found within elasticsearch [' + str(resp['hits']['total']['value']) +']')
				since_id = resp['hits']['hits'][0]['_id']
				logger.info('Latest reply/mention tweet is ' + str(since_id))
			else:
				logger.info('No reply/mention tweets found within elasticsearch')

			logger.info("Initializing procedure of fetching latest tweet replies/mentions of user [" + screen_name +"]")

			q = "to:%s" % screen_name

			while True:
				try:
					# -----------------------------------------------------------------------
					# Using the Twitter Search API we will search for all replies addressed to a twitter user account.
					# This search will result to 1. Replies of a user's tweets and 2. Any other tweets in which this
					# user was mentioned(!)
					# 1. We will use this to track all replies to a tweet
					# 2. Analyze any mentions of a twitter user
					# Twitter API docs:
					# https://developer.twitter.com/en/docs/tweets/search/api-reference/get-search-tweets
					# -----------------------------------------------------------------------
					new_replies = api.search(q=q, count = count, max_id = max_id, since_id = since_id)
					if len(new_replies) == 0:
						logger.info(
							"No new reply/mention tweets for [" + screen_name +
							"]. Exiting while loop to prepare saving")
						break
					max_id = new_replies[-1].id - 1
					all_replies.extend(new_replies)
					logger.info("Total obtained replies/mentions for [" + screen_name + "]:" + str(len(all_replies)))
				except tweepy.RateLimitError:
					limit_exception_handling(api)
			logger.info("Data acquisition is now completed for [" + screen_name + "]. Exiting fetch tweets method")
			return all_replies


if __name__ == '__main__':
	logger.info("==================================================================================================")
	logger.info("TWITTER REPLIES STARTED ON " + str(datetime.datetime.now()))
	logger.info("==================================================================================================")

	try:

		# -----------------------------------------------------------------------
		# Load Config
		# -----------------------------------------------------------------------
		config = {}
		logger.info('Reading Config File')
		logger.info(os.getcwd())
		config_path = os.path.join(os.path.dirname(__file__), 'config.py')
		exec(compile(open(config_path, "rb").read(), config_path, 'exec'), config)
		logger.info('Config File was read successfully')

		logger.info('Creating Redis Connection Client')
		redis_client = redis.Redis(host=config["redis_host"], port=config["redis_port"], password=config["redis_password"])

		# -----------------------------------------------------------------------
		# Load initial tweet_count constant if not available in config.py
		# -----------------------------------------------------------------------
		if "tweet_count" not in config:
			config["tweet_count"] = 200
		tweet_count = config["tweet_count"]

		# -----------------------------------------------------------------------
		# Create twitter API object
		# -----------------------------------------------------------------------
		auth = tweepy.OAuthHandler(config["consumer_key"], config["consumer_secret"])
		auth.set_access_token(config["access_key"], config["access_secret"])
		api = tweepy.API(auth)
		_original_twitter_api = api

		# -----------------------------------------------------------------------
		# Retrieve declared services' tweeter screen names for tweet and retweet retrieval
		# -----------------------------------------------------------------------
		elastic_endpoint = config["elastic_endpoint"]
		elastic_timeline_index = config["elastic_timeline_index"]

		while redis_client.llen(config["redis_twitter_services_list"]) is not 0:
			logger.info("==================================================================================================")
			service = redis_client.lpop(config["redis_twitter_services_list"]).decode('utf-8')
			service = json.loads(service)
			logger.info(service)

			# if there is a new pair of oath_token/secret obtained from the organisation let us use that as well
			if service['_source']['twitter_oauth_token'] and service['_source']['twitter_oauth_secret']:
				logger.info(
					'Twitter Account has its own oauth_key and oauth_secret... switching to those credentials to'
					' perform the requests'
				)
				auth = tweepy.OAuthHandler(config["consumer_key"], config["consumer_secret"])
				auth.set_access_token(service['_source']['twitter_oauth_token'], service['_source']['twitter_oauth_secret'])
				api = tweepy.API(auth)
			else:
				# otherwise restore the original twitter api object
				logger.info('Twitter Account hasn\'t provided any oauth_key and oauth_secret...')
				api = _original_twitter_api

			# -----------------------------------------------------------------------
			# from this point and on we need to scan and retrieve all tweet replies from every known tweet within ES
			# -----------------------------------------------------------------------	
			screen_name = service['_source']['twitter_screen_name']
			logger.info('Twitter User Id : ' + screen_name)
			replies = fetch_replies(api, elastic_endpoint, elastic_timeline_index, screen_name, tweet_count)
			if replies and len(replies):
				semantic_tweets = []
				logger.info("Replies/mentions to be saved [" + str(len(replies)) + "]")
				for tw in replies:
					semantic_tweets.append(json.loads(json.dumps(tw._json)))
					response = requests.post(
						elastic_endpoint + elastic_timeline_index + '/_doc/' + tw.id_str, data=json.dumps(tw._json),
						headers={'Content-Type': 'application/json'}
					)
					if response.status_code is not 201:
						print(response.text)
				if config["to_semantic_redivert"] is True:
					multipart_form_data = {
						"input": ('input.json', json.dumps(semantic_tweets))
					}
					url = config["path"]
					querystring = {"pipeline": config["pipeline"]}
					response = requests.request("POST", url, files=multipart_form_data, params=querystring)
					logger.info("Linked Pipes Response is:" + response.text)
					logger.info("Data insertion is now completed for [" + screen_name + "]")
				else:
					logger.info("Semantic Transformation is disabled")
			logger.info("==================================================================================================")
		logger.info("Twitter Feed Handler completed successfully. Exiting....")
	except KeyError as ex:
		logger.error('Key' + str(ex.args) + 'does not exists')
		raise ex
	except Exception as ex:
		logger.error('Exception :' + str(ex))
		logger.error("Twitter Feed Handler is now exiting")
		exit()
