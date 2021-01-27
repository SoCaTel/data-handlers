#!/bin/bash

echo "======================================"
echo "Docker Build ALL"
echo "======================================"

echo "Build Loader"
cd handler/loader
./docker_build.sh

echo "Build Feed"
cd ../../feed/
./docker_build.sh

echo "Build Replies"
cd ../replies/
./docker_build.sh
