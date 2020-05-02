#!/bin/bash

# Check arguments
#
# Script arguments:
#   $1 Configuration target: poll or push
#   $2 Name of configuration file (output file)
if [ "$#" -ne 2 ]
then
    echo "USAGE: $0 target output_file" >&1
    exit 1    
fi

target=$1
outfile=$2

# This function prompts for a value and writes an environment variable
# assignement to the output file.
# 
# Arguments:
#   $1 Environment variable name
#   $2 Prompt text
function config {
    varname=$1
    prompt=$2
    
    echo -n "$prompt: "
    read varval
    echo "export $varname=\"$varval\"" >> configtmpfile
}

if [ "$target" = "poll" ]
then
    config BOT_APP_KEY "Application key"
    config BOT_APP_SECRET "Application secret"
    config BOT_ACCESS_TOKEN "Access token"
    config BOT_TOKEN_SECRET "Access token secret"
    config BOT_TARGET "Screen name of the Twitter account being replied to"
    config BOT_SOURCE "Source label of target tweets"
elif [ "$target" = "push" ]
then
    config STACK "Name or unique ID of your CloudFormation stack"
    config REGION "AWS region where CloudFormation stack is deployed"
else
    echo "Unknown configuration target $target" >&1
    exit 1   
fi

# Output is first written to a temporary file and then moved. We do this
# because, otherwise, if the caller interrupts configuration (Ctrl-C), they end
# up with incomplete configuration in the file. More importantly, make will
# consider this incomplete configuration file "up to date" and will not call
# this script again.
mv configtmpfile $outfile
echo "Configuration complete."
