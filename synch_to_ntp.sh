#!/bin/sh
# can be done directly in cronjob tab or through this sh file
# 1. change permissions to file: chmod a+rx script_name.sh
# 2. can be set up as cron job every minute: * * * * * ntpdate -u ntp1.rwth-aachen.de
exec ntpdate -u ntp1.rwth-aachen.de