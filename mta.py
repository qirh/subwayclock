#!/usr/bin/python3
#
# Author: Alan N. Light
#
# Provides a simple interface to train arrival times from the MTA's
# data feeds. A MTA API key is required which must be in the file 'apikey.txt'.
# The interface consists of the getTrainTimes function which takes two
# arguments, the station id's of the uptown and downtown platforms of the
# station we are querying. What will be returned is a 4-tuple which will
# contain:
# 1. A list of the ids of the uptown trains (e.g. "A","1","Q","F", etc.)
# 2. A list of the arrival times of the uptown trains expressed as number
#    of minutes from the current time.
# 3. Same as #1, but for the downtown train
# 4. Same as #2, but for the downtown train
#

from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict
import requests
import time
import sys
from datetime import datetime

# Get our API key from file
apikeyfile = 'apikey.txt'
try:
    with open(apikeyfile) as f:APIKey=f.read().rstrip()
except:
    sys.exit("ERROR: Unable to read API key from file %s"%(apikeyfile))

NQRWfeednum = '16' # Feed number for N,Q,R,W trains
BDFMfeednum = '21' # Feed number for B,D,F,M trains
S123456feednum = '1' # Feed number for S,1,2,3,4,5,6 trains
ACEHfeednum = '26' # Feed number for A,C,E,H trains
Lfeednum = '2' # Feed number for the L train
Gfeednum = '31' # Feed number for the G train
JZfeednum = '36' # Feed number for the JZ trains
Sevenfeednum = '51' # Feed number for the 7 train
SIRfeednum = '11' # Feed number for the Staten Island Railway

# List of feeds (in order) that we'll check for arrival times.
# The order of this list will be optimized based on the
# feeds most likely to have the trains in which we are interested
feedsToCheck = [NQRWfeednum, BDFMfeednum, S123456feednum, ACEHfeednum,
                Lfeednum, Gfeednum, JZfeednum, Sevenfeednum, SIRfeednum]

# Dictionary of feed "scores." The score will simply be the number of times
# that our desired station was found in a given feed. This will then be used
# to optimize the order of 'feedsToCheck'
feedScores = dict.fromkeys(feedsToCheck,0)

# MTA URL
url = 'http://datamine.mta.info/mta_esi.php'

def gettimes(feednum, s1, s2):

    uptownTimes = []
    downtownTimes = []
    uptownTrainIDs = []
    downtownTrainIDs = []
    route_id = ""

    # Request parameters
    params = {'key': APIKey, 'feed_id': feednum}

    # Get the train data from the MTA
    response = requests.get(url, params=params, timeout=30)

    # Parse the protocol buffer that is returned
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    # Get a list of all the train data
    subway_feed = protobuf_to_dict(feed) # subway_feed is a dictionary
    realtime_data = subway_feed['entity'] # train_data is a list

    # A list of all the arrivals we found for our station in the given feed
    arrivals = []

    # Iterate over each train arrival
    for train in realtime_data:
        # If there is a trip update with a stop time update
        if train.get('trip_update'):
            if (train['trip_update'].get('stop_time_update')):
                # get for each stop time update that is at our stop
                for update in train['trip_update'].get('stop_time_update'):
                    stop_id = update['stop_id']

                    if (stop_id in [s1, s2]):

                        # Get the number of seconds from now to the arrival time
                        elapsed = update['arrival']['time']-time.mktime(datetime.now().timetuple())

                        # If we alredy missed it, skip it
                        if (elapsed < 0):
                            continue

                        route_id = (train['trip_update']['trip']['route_id'])[0]

                        # Calculate minutes and seconds until arrival
                        mins = int(elapsed / 60)
                        secs = int(elapsed % 60)

                        # Round to nearest minute
                        if (secs > 30):
                            mins = mins + 1

                        # Skips zeros
                        if (mins == 0):
                            continue

                        if (stop_id == s1):
                            # Check for dupes and then append
                            if (mins not in uptownTimes):
                                uptownTimes.append(mins)
                                uptownTrainIDs.append(route_id)

                        if (stop_id == s2):
                            if (mins not in downtownTimes):
                                downtownTimes.append(mins)
                                downtownTrainIDs.append(route_id)

    # Sort the results
    if (len(uptownTimes) != 0):
        (uptownTimes, uptownTrainIDs) = tuple(zip(*sorted(zip(uptownTimes, uptownTrainIDs), key=lambda p: p[0])))

    if (len(downtownTimes) != 0):
        (downtownTimes, downtownTrainIDs) = tuple(zip(*sorted(zip(downtownTimes, downtownTrainIDs), key=lambda p: p[0])))


    # Return our results as a tuple
    return(uptownTrainIDs, uptownTimes, downtownTrainIDs, downtownTimes)

def getTrainTimes(ourUptownStation, ourDowntownStation):
    global feedsToCheck
    global feedScores

    uptownTrainIDs = []
    uptownTimes = []
    downtownTrainIDs = []
    downtownTimes = []

    # Check each of the feeds in turn for trains arriving at our station until
    # we get some results
    for f in feedsToCheck:
        times = gettimes(f, ourUptownStation, ourDowntownStation)
        # If we found our station in the feed, then increment the feed's score and break out
        if (len(times[0]) != 0):
            # Found uptown
            feedScores[f] += 1
            uptownTrainIDs = times[0]
            uptownTimes = times[1]
            if (len(downtownTrainIDs) != 0):
                # Found both
                break
        if (len(times[2]) != 0):
            # Found downtown
            feedScores[f] += 1
            downtownTrainIDs = times[2]
            downtownTimes = times[3]
            if (len(uptownTrainIDs) != 0):
                # Found both
                break


    # Sort 'feedsToCheck' so that we are checking the most likely feeds first
    feedsToCheck = sorted(feedsToCheck, reverse=True, key=lambda p: feedScores[p])

    return (uptownTrainIDs, uptownTimes, downtownTrainIDs, downtownTimes)


# Test case, plug in the names of the subway stops you want to test
if __name__ == '__main__':
    if (len(sys.argv) < 3):
        print(getTrainTimes("Q03N","Q03S"))
    else:
        print(getTrainTimes(sys.argv[1],sys.argv[2]))
