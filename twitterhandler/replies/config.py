# --------------------------------------------------------------------------------
# SoCaTel - Twitter Feed Container
# These tokens are needed for user authentication.
# Credentials can be generates via Twitter's Application Management:
# https://apps.twitter.com/app/new
# --------------------------------------------------------------------------------


# ===============================================================================
# Twitter Consumer and Access keys
# ===============================================================================
consumer_key = "<insert_a_twitter_consumer_key_here>"
consumer_secret = "<insert_a_twitter_consumer_secret_here>"
access_key = "<insert_a_twitter_access_key_here>"
access_secret = "<insert_a_twitter_access_secret_here>"
# ===============================================================================


# ===============================================================================
# Elastic Search Endpoint Definition
# ===============================================================================
# SoCaTel Knowledge Base Deployment
# ===============================================================================
elastic_endpoint = "http://<elastic_username>:<elastic_password>@<elastic_host>:9200/"
elastic_timeline_index = "kb_twitter_raw"
# ===============================================================================


# ===============================================================================
# Redis Cache Local configuration
# ===============================================================================
# SoCaTel Knowledge Base Deployment
# ===============================================================================
redis_host = "socatel-redis"
redis_port = 6379
redis_password = "default_soca_redis"
redis_twitter_services_list = "twitter_feed_services"


# ===============================================================================
# Twitter Feed Configuration
# ===============================================================================
tweet_count = 200
# ===============================================================================

# ===============================================================================
# Linked Pipes ETL Configuration
# ===============================================================================
to_semantic_redivert = True
path = "http://<insert_graphql_host>:32800/resources/executions"
pipeline = "http://<insert_graphql_host>:32800/resources/pipelines/1552388831995"
# ===============================================================================
