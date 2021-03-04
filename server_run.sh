#!/bin/bash
for i in 1 2 3 4 5
do
   for gpu in 0 1 2 3 4 5 6 7
   do
    docker-compose run --name "konsti_product_GPU$gpu""_$i" -d -e NVIDIA_VISIBLE_DEVICES="$gpu" server_production
   done
done