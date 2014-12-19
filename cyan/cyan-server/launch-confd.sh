#!/bin/sh
sleep 5
curl -L http://127.0.0.1:4001/v2/keys/cyan -XPUT -d dir=true
/confd -confdir /config/confd/ -backend etcd -node 127.0.0.1:4001 -interval 1