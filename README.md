# twitter-goodbotbot
Code behind the [@GoodBotBot](https://twitter.com/GoodBotBot) Twitter bot account

## What Is This?

This Twitter bot polls the Twitter API for automatic tweets by specific bot
account and replies to each tweet with a congratulatory message such as "good
job" or "good bot".

## Why Do This?

The [@xkcdComic](https://twitter.com/xkcdComic) Twitter account posts
[xkcd](https://xkcd.com/) comics on Twitter. Each time a new comic is posted,
the [@XKCDAltTextBot](https://twitter.com/XKCDAltTextBot) automatically replies
with that comic strip's alt/title text. Other Twitter users then usually
congratulate the bot with a "good bot" reply. This bot aims to automate the
process of congratulating [@XKCDAltTextBot](https://twitter.com/XKCDAltTextBot).
Because it's fun.

## How it Works

This Twitter bot is intended to be deployed in the [AWS](https://aws.amazon.com/)
cloud. The core of the functionality is a
[Lambda](https://aws.amazon.com/lambda/) function written in Python that uses
the [Tweepy](http://docs.tweepy.org/en/latest/) library to interact with the
[Twitter API](https://developer.twitter.com/en/docs).

A periodic
[CloudWatch Events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/WhatIsCloudWatchEvents.html)
rule calls the Lambda function to poll for new tweets by the target account
every two minutes. If a new tweet is detected, the Lambda function starts a new
execution of a [Step Functions](https://aws.amazon.com/step-functions/) state
machine. That state machine calls the Lambda function again with the tweet ID as
argument to have it reply to the new tweet.

The Step Functions state machine serves two purposes:
* It handles retries in case of failure. The bot will retry for about 4 hours
  with exponential backoff for most types of failures, and will wait a little
  over 15 minutes before retrying for some failures such as if the rate limits
  of the Twitter API are reached or for failures that will likely require human
  intervention.
* Robustness: the name of each execution of a standard state machine has to be
  unique, otherwise the execution fails. This property is used to ensure the
  bot never tries to reply many times to the same tweet concurrently, even if
  the Lambda function is called multiple times for polling.

The whole stack is described in a
[CloudFormation](https://aws.amazon.com/cloudformation/) template for easy
deployment.

## How to Run

### Step 1: Get Credentials

For any use of the Twitter API, you first need to apply for a
[Twitter developer account](https://developer.twitter.com/en) and then create
a [Twitter API application](https://developer.twitter.com/en/apps) for that bot.
Make sure you read, understand and comply with all relevant Twitter policies,
including (but not limited to):
* The [Twitter Rules](https://help.twitter.com/en/rules-and-policies/twitter-rules).
* The [Developer Agreement](https://developer.twitter.com/en/developer-terms/agreement).
* The [automation rules](https://help.twitter.com/en/rules-and-policies/twitter-automation).

Once you create a Twitter application, you will be able to obtain an application
key and associated secret that will allow your application to authenticate to
the Twitter API. You will also be able to generate an access token and
associated secret specific to your account that will allow you application to
take actions such as tweeting from that account.

### Step 2: Deploy the Stack

Use the [AWS Console](https://aws.amazon.com/console/) to create a
CloudFormation stack from the provided template file (``cloudformation.json``).

The stack requires the following parameters:

* **ParamAppKey**: Application/API key for the Twitter API.
* **ParamAppSecret**: Application/API secret for the Twitter API.
* **ParamUserKey**: Access token for the Twitter API.
* **ParamUserSecret**: Access token secret for the Twitter API.
* **ParamReplyToName**: Screen name of the Twitter account monitored for tweets.
* **ParamSource**: [Source label](https://help.twitter.com/en/using-twitter/how-to-tweet#source-labels)
of tweets that will get a reply. This bot uses the source label to identify
tweets that are sent automatically.

The inline code for the Lambda function in the CloudFormation template creates
a simple "Hello World" Lambda function, not the final code which will be
uploaded in the next step. If all goes well, at this point, the Lambda function
should be logging "Hello World" in the
[CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
once every 2 minutes.

### Step 3: Build and Upload the Deployment Package

To build a Lamba
[deployment package](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html),
simply run ``make`` in the root of your working copy. The provided Makefile
uses [pip](https://pypi.org/project/pip/) to install all needed dependencies in
a temporary directory (named ``target``) inside your working copy. It then zips
these dependencies together with the code for the Lambda function
(``index.py``). The resulting zip file (``goodbotbot.zip``) can be uploaded to
Lambda.

When the deployment package has been built, use the AWS Console to update the Lambda
function created by the CloudFormation stack.
