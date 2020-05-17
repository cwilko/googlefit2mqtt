#! /bin/ash

run(){
    echo "Starting python process"
    while true; do          
        python main.py
        echo "Error during python process."
        sleep 300
        echo "Restarting..."
    done
}

run & wait $! # handle sigterm