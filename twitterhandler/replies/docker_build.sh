#!/bin/bash
PROJECT_NAME=socatel
CONTAINER_NAME=sct-twitter-replies
IMAGE_NAME="$PROJECT_NAME/$CONTAINER_NAME"

# Initial Threadpool size
THREADPOOL_SIZE=2

# Remove previous socatel-twitter-feed container (if any)
for thread_item in `seq 1 $THREADPOOL_SIZE`
do
  echo "Removing $CONTAINER_NAME-TH-$thread_item"
  docker container rm $CONTAINER_NAME-TH-$thread_item
done

# Build docker image
docker build -t $IMAGE_NAME:latest .

# Create docker container but do not run it
for thread_item in `seq 1 $THREADPOOL_SIZE`
do
  echo "Creating $CONTAINER_NAME-TH-$thread_item"
  docker create -ti --network=socatel-network --name $CONTAINER_NAME-TH-$thread_item $IMAGE_NAME:latest
done