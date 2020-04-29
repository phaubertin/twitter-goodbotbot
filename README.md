# twitter-goodbotbot
Code behind the [@goodbotbot](https://twitter.com/GoodBotBot) Twitter bot account

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
