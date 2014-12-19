#!/bin/bash

PID=$(docker run -d -p $2:5000 -e color=$1 -v $(pwd):/code bluegreen)
echo $(docker inspect --format='{{.Name}}' $PID | cut -c2-90)
docker attach $PID
