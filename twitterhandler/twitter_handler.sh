#!/bin/bash

FEED_CONTAINER_NAME=sct-twitter-feed
REPLIES_CONTAINER_NAME=sct-twitter-replies

# Initial Threadpool size
THREADPOOL_SIZE=2

echo "======================================================================="
echo -e "\t \t STARTING TWITTER HANDLER"
echo -e "** to observe logs of a container type $ docker logs \$container_name"
echo "======================================================================="

#STARTING twitter loader that loads all services to REDIS Cache
echo "Starting sct-twitter-loader"
docker start sct-twitter-loader
echo "sct-twitter-loader STARTED SUCCESSFULLY"

# Start docker container for twitter feed and replies
for thread_item in `seq 1 $THREADPOOL_SIZE`
do
  echo "Starting $FEED_CONTAINER_NAME-TH-$thread_item"
  docker start $FEED_CONTAINER_NAME-TH-$thread_item

  echo "Starting $REPLIES_CONTAINER_NAME-TH-$thread_item"
  docker start $REPLIES_CONTAINER_NAME-TH-$thread_item
  
done

echo "Twitter Handler Container is now completed"
