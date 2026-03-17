#!/bin/sh
python WeatherAPI.py --serve &
python LocationAPI.py --serve &
wait