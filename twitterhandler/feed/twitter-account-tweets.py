#/usr/bin/python
# encoding: utf-8

#-----------------------------------------------------------------------
# SoCaTel Twitter Feed
# twitter-user-timeline
#  - displays a user's current timeline.
#-----------------------------------------------------------------------

import os
import json
import time
import redis
import tweepy
import requests
import datetime
import coloredlogs, logging

logger = logging.getLogger('TWITTER_HANDLER')
coloredlogs.install(level='DEBUG', logger=logger)


# -----------------------------------------------------------------------
# ELASTICSEARCH QUERY/UTILS METHOD LIST
# -----------------------------------------------------------------------

def qr_latest_tweet(screen_name):
	"""
	Query returns the latest tweet on a descending order based on the id field
	"""
	query = {
		"query": {
			"constant_score": {
				"filter": {
					"term": {
						"user.screen_name": screen_name,
						"in_reply_to_user_id": None
					}
				}
			}
		},
		"sort": [
			{
				"id":
					{
						"order": "desc"
					}
			}
		],
		"size": 1
	}
	return query


def qr_number_of_tweets(screen_name):
	"""
	Query returns the number of tweets for a specific screen name
	"""
	query = {
		"query": {
			"constant_score": {
				"filter": {
					"term": {
						"user.screen_name": screen_name,
						"in_reply_to_user_id": None
					}
				}
			}
		}
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


# ---------------------------------------------------------------------
# TWITTER HELPER METHOD LIST
# ---------------------------------------------------------------------
def limit_exception_handling(api):
	"""
	Limit exception handling method is able to read the limit constraint from the api. This
	results to how many msec the API should not be used. A timer is then being used as a stalling 
	mechanism to stall the API from requesting data
	"""
	limit = api.rate_limit_status()
	logger.info('Error Twitter Limit Exception: ' + json.dumps(limit, indent=4, sort_keys=True))
	sleep_interval = limit['resources']["statuses"]["/statuses/user_timeline"]["reset"] - time.time()
	if sleep_interval > 0:
		logger.info('Sleeping for ' + str(sleep_interval) + 'msec')
		time.sleep(sleep_interval)


def fetch_tweets(twitter_api, index_name, screen_name, tweet_count):
	"""
	Fetch tweets method uses twitter api to retrieve newer tweets from known services via screen_name
	"""
	try:
		logger.info('Fetching tweets for ' + screen_name)
		all_tweets = []
		since_id = None
		max_id = None
		logger.info(
			"Performing a search request on elasticsearch to bring the total amount of tweets we have so far for " +
			screen_name)
		search_path = elastic_endpoint + index_name + '/_count'
		query = qr_number_of_tweets(screen_name.lower())
		resp = requests.get(search_path, json=query).json()
		if resp['count'] != 0:
			logger.info('Existing tweets found within elasticsearch [' + str(resp['count']) + ']')
			search_path = elastic_endpoint + index_name + '/_search'
			query = qr_latest_tweet(screen_name.lower())
			get_latest_tweets = requests.get(search_path, json=query).json()
			since_id = get_latest_tweets['hits']['hits'][0]['_source']['id']
			logger.info('Latest tweet is ' + str(since_id))
		else:
			logger.info('No tweets found within elasticsearch')
		while True:
			try:
				# -----------------------------------------------------------------------
				# query the user timeline.
				# twitter API docs:
				# https://dev.twitter.com/rest/reference/get/statuses/user_timeline
				# -----------------------------------------------------------------------
				new_tweets = twitter_api.user_timeline(screen_name=screen_name, since_id=since_id, max_id=max_id, count=200)
				if len(new_tweets) != 0:
					max_id = new_tweets[-1].id -1
					all_tweets.extend(new_tweets)
					logger.info("Total obtained tweets for [" + screen_name + "]:" + str(len(all_tweets)))

				if len(new_tweets) == 0 or len(new_tweets) < tweet_count:
					logger.info("No new tweets for [" + screen_name + "]. Exiting while loop to prepare saving")
					break

			except tweepy.RateLimitError:
				limit_exception_handling(twitter_api)
		logger.info("Data acquisition is now completed for [" + screen_name + "]. Exiting fetch tweets method")
		return all_tweets
	except Exception as ex:
		logger.error('Exception:' + str(ex))
		raise ex


if __name__ == '__main__':
	logger.info("==================================================================================================")
	logger.info("TWITTER FEED STARTED ON " + str(datetime.datetime.now()))
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
		redis_client = redis.Redis(
			host=config["redis_host"], port=config["redis_port"], password=config["redis_password"]
		)

		# -----------------------------------------------------------------------
		# Load initial tweet_count constant if not available in config.py
		# -----------------------------------------------------------------------
		if "tweet_count" not in config:
			config["tweet_count"] = 200
		tweet_count = config["tweet_count"]

		#-----------------------------------------------------------------------
		# create twitter API object
		#-----------------------------------------------------------------------		
		auth = tweepy.OAuthHandler(config["consumer_key"],config["consumer_secret"])
		auth.set_access_token(config["access_key"], config["access_secret"])
		api = tweepy.API(auth)
		_original_twitter_api = api

		#-----------------------------------------------------------------------
		# Retrieve declared services' twitter screen names for tweet and retweet retrieval from redis cache
		#-----------------------------------------------------------------------
		elastic_endpoint = config["elastic_endpoint"]
		elastic_timeline_index = config["elastic_timeline_index"]

		while redis_client.llen(config["redis_twitter_services_list"]) is not 0:
			logger.info("==================================================================================================")
			service = redis_client.lpop(config["redis_twitter_services_list"]).decode('utf-8')
			service = json.loads(service)
			logger.info(service)

			# if there is a new pair of oath_token/secret obtained from the organisation let us use that as well
			if service['_source']['twitter_oauth_token'] and service['_source']['twitter_oauth_secret']:
				logger.info('Twitter Account has its own oauth_key and oauth_secret... switching to those credentials to perform the requests')
				auth = tweepy.OAuthHandler(config["consumer_key"],config["consumer_secret"])
				auth.set_access_token(service['_source']['twitter_oauth_token'], service['_source']['twitter_oauth_secret'])
				api = tweepy.API(auth)
			else:
				# otherwise restore the original twitter api object
				logger.info('Twitter Account hasn\'t provided any oauth_key and oauth_secret...')
				api = _original_twitter_api


			#-----------------------------------------------------------------------
			# from this point and on we need to scan and retrieve all tweets from twitter API
			#-----------------------------------------------------------------------		
			screen_name = service['_source']['twitter_screen_name']
			logger.info('Organisation Name: ' + service['_source']['organisation_name'])


			if screen_name is not None:

				logger.info('Twitter User Id : ' + screen_name)
				tweets = fetch_tweets(api, elastic_timeline_index, screen_name, tweet_count)
				if tweets and len(tweets):
					#to_bulk_add = twitter_bulk_save(tweets)
					semantic_tweets = []
					logger.info("Feed to be saved [" + str(len(tweets)) + "]")
					for tw in tweets:
						# Preparing the semantic pre-processing array
						semantic_tweets.append(json.loads(json.dumps(tw._json)))
						response = requests.post(
							elastic_endpoint + elastic_timeline_index + '/_doc/' + tw.id_str, data=json.dumps(tw._json),
							headers={'Content-Type': 'application/json'}
						)
						if response.status_code is not 201:
							print(response)
					logger.info("Data insertion is now completed for [" + screen_name + "]")

					if config["to_semantic_redivert"] is True:
						multipart_form_data = {
							"input": ('input.json', json.dumps(semantic_tweets))
						}
						url = config["path"]
						querystring = {"pipeline": config["pipeline"]}
						response = requests.request("POST", url, files=multipart_form_data, params=querystring)
						logger.info("Linked Pipes Response is:" + response.text)
						logger.info("Semantic annotation is now completed!")
					else:
						logger.info("Semantic Transformation is disabled")
				else:
					logger.info("No data insertion required for ["+ screen_name  +"]")
			else:
				logger.warn('There is no screen_name available')
			logger.info(
				"=================================================================================================="
			)

		logger.info("Twitter Feed Handler completed successfully. Exiting....")
	except KeyError as ex:
		logger.error('Key' + str(ex.args) + 'does not exists')
		raise ex
	except Exception as ex:
		logger.error('Exception :' + str(ex))
		logger.error("Twitter Feed Handler is now exiting")
		exit()
