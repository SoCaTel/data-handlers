#!/bin/bash

NETWORK_NAME=socatel-network
echo "Checking if $NETWORK_NAME exists" 
if [ -z $(docker network ls --filter name=^${NETWORK_NAME}$ --format="{{ .Name }}") ] ; then 
    echo "Creating $NETWORK_NAME...." 
     docker network create ${NETWORK_NAME} ; 
else
    echo "$NETWORK_NAME exists.. do nothing" 
fi

# Container name
CONTAINER_NAME=sct-re-index
IMAGE_NAME=socatel/$CONTAINER_NAME
# Remove previous socatel-twitter-handler container (if any)

echo "Removing container [$CONTAINER_NAME]"
docker container rm $CONTAINER_NAME

# Build docker image
echo "Building new image [$IMAGE_NAME:latest]"
docker build -t $IMAGE_NAME:latest .

# Create docker container but do not run it
echo "Creating new container [$CONTAINER_NAME]"
docker create --name $CONTAINER_NAME --network=socatel-network -it $IMAGE_NAME:latest

echo "Starting new container [$CONTAINER_NAME]"
docker start $CONTAINER_NAME
