#!/usr/bin/env python
#
# Copyright (c) 2020 Philippe Aubertin
# All rights reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""GoodBotBot Twitter bot."""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import random
import sys
import tweepy

from datetime import datetime, timezone

# Seed random number generator during initialization.
random.seed()

# We use the presence of the AWS_EXECUTION_ENV environment variable to detect
# that the code is running in AWS Lambda.
if os.environ.get('AWS_EXECUTION_ENV', None):
    # Import boto3 package needed to invoke the Step Function state machine
    # from the AWS Lambda function.
    import boto3
    
    # Patch supported libraries to instrument them with AWS X-Ray. In our case,
    # this means the requests library used by Tweepy.
    #
    # Both the patching and the import are done conditionally to ensure there
    # is a dependency on the AWS X-Ray SDK only when the code runs on AWS Lambda. 
    #
    # Performance note: previously, we did this in the AWS Lambda handler function
    # (i.e. the handler() function) instead of here. This was adding 5.5 seconds
    # to each invocation.
    from aws_xray_sdk.core import patch_all
    patch_all()

# Default maximum age of a tweet to which the bot will reply, in minutes.
DEFAULT_MAXAGE = 6 * 60

MESSAGES = frozenset([
    'Admirable bot.',
    'Amazing bot.',
    'Awesome bot.',
    'Brilliant bot.',
    'Cool bot.',
    'Excellent bot.',
    'Exceptional bot.',
    'Extraordinary bot.',
    'Fantastic bot.',
    'Good bot.',
    'Grandiose bot.',
    'Impressive bot.',
    'Incredible bot.',
    'Magnificient bot.',
    'Marvelous bot.',
    'Noble bot.',
    'Outstanding bot.',
    'Phenomenal bot.',
    'Remarkable bot.',
    'Sensational bot.',
    'Sublime bot.',
    'Superb bot.',
    'Wonderful bot.',
    'The best bot.',
    'Thank you for your assiduity.',
    'Thank you for your conscientiousness.',
    'Thank you for your diligence.',
    'Thank you for your generous effort.',
    'Thanks!',
    'Much thanks.',
    'Thanks so much.',
    'Thank you for posting this.',
    'Good job.',
    'Splendid job.',
    'I appreciate your effort.',
    'I appreciate your diligence.',
    'I appreciate your work.',
    'I am grateful for your work.',
    'Well done.',
    'Continue your great work.'
])

class GoodBotBotException(Exception):
    """Base class for exceptions thrown by this application"""
    
    pass

class ConfigurationException(GoodBotBotException):
    """Exception that indicates a configuration error such as a missing configuration option."""
    
    pass
    
class NoTimelineException(GoodBotBotException):
    """Exception that indicates the user timeline of the controlled Twitter account is empty.
    
    Even though this might simply be because the account never tweeted, out of
    an abundance of caution, this bot will not tweet in this case. We want to
    be sure the bot can see the replies when checking whether it already replied
    to a specific tweet, because we don't want the bot to reply repeatedly to
    the same tweet.
    """
    
    pass

def set_defaults(config):
    """Set configuration defaults"""
    
    if(not config.get('maxage', None)):
        config['maxage'] = DEFAULT_MAXAGE

def load_configuration(config=None, environ=None):
    """Get configuration options from environment.
    
    Arguments:
    config -- initial configuration dictionary (default empty dictionary)
    environ -- environment dictionary (default os.environ)
    
    Returns a dictionary containing configuration.
    
    Throws ConfigurationException if a configuration option is missing.
    """
    
    if environ is None:
        environ = os.environ
    
    if config is None:
        config = {}

    missing         = []
    config_options  = [
        {
            'key'       : 'app_key',
            'environ'   : 'BOT_APP_KEY',
            'is_int'    : False
                
        },
        {
            'key'       : 'app_secret',
            'environ'   : 'BOT_APP_SECRET',
            'is_int'    : False
        },
        {
            'key'       : 'access_token',
            'environ'   : 'BOT_ACCESS_TOKEN',
            'is_int'    : False
        },
        {
            'key'       : 'token_secret',
            'environ'   : 'BOT_TOKEN_SECRET',
            'is_int'    : False
        },
        {
            'key'       : 'target',
            'environ'   : 'BOT_TARGET',
            'is_int'    : False
        },
        {
            'key'       : 'source',
            'environ'   : 'BOT_SOURCE',
            'is_int'    : False
        },
        {
            'key'       : 'maxage',
            'environ'   : 'BOT_MAXAGE',
            'is_int'    : True
        }
    ]
    
    # Read configuration options from environment.
    for option in config_options:
        value = environ.get(option['environ'], None)
        
        if value is not None:
            if option['is_int']:
                config[option['key']] = int(value)
            else:
                config[option['key']] = value
    
    # Set default values
    set_defaults(config)
    
    # Ensure all required configuration options are present.
    for option in config_options:
        if option['key'] not in config:
            missing.append(option['environ'])
    
    if missing:
        raise ConfigurationException(
            'Missing configuration option(s): ' + ', '.join(missing))
    
    return config

def instanciate_api(config):
    """Instanciate the Tweepy API object."""
    
    auth = tweepy.OAuthHandler(config['app_key'], config['app_secret'])
    auth.set_access_token(config['access_token'], config['token_secret'])
    
    return tweepy.API(auth)

def pretty_duration(seconds):
    """Return a human-readable string for the specified duration"""
    
    if seconds < 2:
        return '%d second' % seconds
    elif seconds < 120:
        return '%d seconds' % seconds
    elif seconds < 7200:
        return '%d minutes' % (seconds // 60)
    elif seconds < 48 * 3600:
        return '%d hours' % (seconds // 3600)
    else:
        return '%d days' % (seconds // (24 * 3600))

def print_rate_limit(response):
    """Retrieve rate limit remaining from response headers and print it."""
    
    reset_header = response.headers.get('x-rate-limit-reset', None)
    
    if reset_header is None:
        reset = '??'
    else:
        try:
            reset_time      = datetime.fromtimestamp(int(reset_header), tz=timezone.utc)
            reset_in        = reset_time - datetime.now(timezone.utc)
            reset           = pretty_duration(reset_in.total_seconds())
        except:
            reset       = '?!?'
    
    print('Rate limit remaining %s/%s resets in %s' % (
        response.headers.get('x-rate-limit-remaining', '??'),
        response.headers.get('x-rate-limit-limit',     '??'),
        reset
    ))

def print_header(response, header):
    """Print a response header."""
    
    print('%s: %s' % (header, response.headers.get(header, '??')))

def get_latest_candidate_tweet(api, config):
    """Find the latest candidate tweet.
    
    In order to be a candidate, the tweet must:
    - Be from the correct user/bot account.
    - Have the correct source (i.e. it must have been posted by the bot).
    - Not be a retweet.
    - Contain the text "Alt/title text:"
    
    Arguments:
    api -- Tweepy API object
    config -- configuration dictionary, see load_configuration()
    """
    
    tweets = api.user_timeline(screen_name=config['target'], count=20)
    print_rate_limit(api.last_response)
    print_header(api.last_response, 'last-modified')
    
    for tweet in tweets:
        if tweet.author.screen_name != config['target']:
            continue
        
        if tweet.source != config['source']:
            continue
        
        if hasattr(tweet, 'retweet_status') and tweet.retweet_status:
            continue
        
        if 'Alt/title text:' not in tweet.text:
            continue
            
        return tweet
    
    # No candidate tweet.
    return None
        
def choose_reply(api, tweet):
    """Choose a reply for the specified tweet if it hasn't been replied to.
    
    Checks the last 20 tweets by the controlled account for a reply to the
    specified tweet. If the tweet has already been replied to, return None.
    Otherwise, return a reply for it.
    """
    
    mytweets = api.user_timeline(count=20)
    
    if len(mytweets) < 1:
        # The user timeline is empty.
        #
        # Even though this might simply be because the account never tweeted,
        # out of an abundance of caution, this bot will not tweet in this case.
        # We want to be sure the bot can see the replies because we don't want
        # the bot to reply repeatedly to a tweet.
        raise NoTimelineException("Controlled account's timeline is empty")
    
    messages = set(MESSAGES)
    
    for mytweet in mytweets:
        # Check if this is a reply to the target tweet.
        if mytweet.in_reply_to_status_id == tweet.id:
            # This is an existing reply to the target tweet.
            return None
        
        # Remove this reply from the set of candidate replies.
        messages = set(x for x in messages if x not in tweet.text)
    
    # Return a random message from the remaining ones.
    return random.sample(messages, 1)[0]
    
def time_since_tweet(tweet, now=None):
    """Get the number of seconds that have elapsed since a tweet was created."""
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    # The date and time reported by the Twitter API is in the UTC time zone.
    # However, the Tweepy library parses this into a "naive" datetime object
    # without timezone information. Let's fix that.
    tweet_time  = datetime.combine(
                    tweet.created_at.date(),
                    tweet.created_at.time(),
                    tzinfo=timezone.utc)
    
    # Compute time elapsed since tweet.
    delta       = now - tweet_time
    seconds     = delta.total_seconds()
    
    if seconds < 0:
        # Clock skew???
        return 0
    else:
        return seconds
        
def print_tweet(tweet):
    """Print some information about a tweet."""
    
    if not tweet:
        print('No tweet')
    else:
        print('.  Tweet ID: ' + tweet.id_str)
        print('.  Created:  ' + str(tweet.created_at))
        print('.  Author:   ' + tweet.author.screen_name)
        print('.  ' + tweet.text)

def choose_candidate_tweet(api, config):
    """Get tweet to which to reply"""
    
    candidate = get_latest_candidate_tweet(api, config)
    
    print_tweet(candidate)
    
    if candidate is None:
        return None
    
    seconds_since = time_since_tweet(candidate)
    
    # Configuration value is in minutes. We convert all time intervals to
    # seconds before comparing and printing.
    maxage = config['maxage'] * 60
    
    print("Tweet was posted %s ago." % pretty_duration(seconds_since))
    
    if seconds_since > maxage:
        print("Tweet was posted more than %s ago." % pretty_duration(maxage))
        return None
        
    reply = choose_reply(api, candidate)
    
    if not reply:
        print('Already replied to this tweet.')
        return None
    
    return candidate

def reply_to_tweet(api, tweet_id, dry_run):
    """Reply to the specified tweet."""
    
    tweet = api.get_status( int(tweet_id) )
    
    print_tweet(tweet)
    
    # When this function returns retval, this return value is propagated by the
    # Lambda handler and becomes the return value of the Lambda function.
    retval = {
        'tweet-id'  : tweet_id,
        'dry-run'   : dry_run
    }
    
    # Choose a random reply from MESSAGES that was not used recently. Returns
    # None if the tweet was already replied to by this bot.
    reply = choose_reply(api, tweet)
    
    if not reply:
        print('Already replied to this tweet.')
    else:
        print("Reply: " + reply)
        
        if dry_run:
            print('Dry run - not sending reply')
        else:
            api.update_status(
                '@%s %s' % (tweet.author.screen_name, reply),
                in_reply_to_status_id = int(tweet_id)
            )
            
            print('Reply tweet sent.')
            
            # Add the reply text to the return value. 
            retval['reply-tweet'] = reply
    
    return retval

def run_state_machine(state_arn, tweet_id):
    """Invoke Step Function state machine
    
    The state machines fullfills two goals:
    1) It manages retries in case sending the reply fails.
    2) We use the enforced unicity of the execution name to ensure the bot will
       attempt to reply to a tweet only once, even if the Lambda function is
       invoked multiple times concurrently.
    """

    client      = boto3.client('stepfunctions')
    execution   = 'GoodBotBot-tweet-id-' + tweet_id
    
    print('Execution name: ' + execution)
    
    client.start_execution(
        stateMachineArn = state_arn,
        # Generating a name that contains the tweet ID ensures the state machine
        # will be run only once for this tweet by the bot.
        name            = execution,
        input           = json.dumps({
            'tweet-id' : tweet_id
        })
    )

def handler(event, context):
    """Aws Lambda Function handler."""
    
    config      = load_configuration()
    api         = instanciate_api(config)
    
    state_arn   = event.get('state-machine-arn',  None)
    tweet_id    = event.get('tweet-id', None)
    dry_run     = event.get('dry-run',  False)
    
    if tweet_id is None:
        # This branch is called by the periodic event rule for polling. It does
        # not have a return value.
        tweet = choose_candidate_tweet(api, config)
        
        if state_arn is None:
            print("Warning: no Step Function state machine ARN provided")
        elif tweet is not None:
            run_state_machine(state_arn, tweet.id_str)
    else:
        # This branch is called by the Step Functions state machine to reply to
        # a specific tweet. It has a return value that contains, among other
        # things, the text of the reply tweet if one is sent.
        print('Tweet ID argument: ' + tweet_id)        
        return reply_to_tweet(api, tweet_id, dry_run)

def main(argv):

    config      = load_configuration()
    api         = instanciate_api(config)
    
    choose_candidate_tweet(api, config)

if __name__ == '__main__':
    main(sys.argv)
