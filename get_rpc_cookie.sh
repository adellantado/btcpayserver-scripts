#!/bin/bash

# Get the cookie from the bitcoin data directory
cookie=$(docker exec -it btcpayserver_bitcoind cat /data/testnet3/.cookie)
echo "Cookie:"
echo "$cookie"