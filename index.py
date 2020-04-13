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

import os
import sys
import tweepy

# Patch supported libraries to instrument them with AWS X-Ray. In our case, this
# means the requests library used by Tweepy.
#
# Both the patching and the import are done conditionally to ensure there is a
# dependency on the AWS X-Ray SDK only when the code runs on AWS Lambda. We use
# the presence of the AWS_EXECUTION_ENV environment variable to detect that the
# code is running in AWS Lambda.
#
# Performance note: previously, we did this in the AWS Lambda handler function
# (i.e. the handler() function) instead of here. This was adding 5.5 seconds to
# each invocation.
if os.environ.get('AWS_EXECUTION_ENV', None):
    from aws_xray_sdk.core import patch_all
    patch_all()

# Default maximum age of a tweet to which the bot will reply, in minutes.
DEFAULT_MAXAGE = 6 * 60

MESSAGES = [    
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
    'Thank you for your assiduity.',
    'Thank you for your conscientiousness.',
    'Thank you for your diligence.',
    'Thank you for your generous effort.',
    'Thank you for your service.',
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
    'Very well done.'
]

class GoodBotBotException(Exception):
    """Base class for exceptions thrown by this application"""
    
    pass

class ConfigurationException(GoodBotBotException):
    """Exception that indicates a configuration error such as a missing configuration option."""
    
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
            'environ'   : 'BOT_APP_KEY'
        },
        {
            'key'       : 'app_secret',
            'environ'   : 'BOT_APP_SECRET'
        },
        {
            'key'       : 'access_token',
            'environ'   : 'BOT_ACCESS_TOKEN'
        },
        {
            'key'       : 'token_secret',
            'environ'   : 'BOT_TOKEN_SECRET'
        },
        {
            'key'       : 'target',
            'environ'   : 'BOT_TARGET'
        },
        {
            'key'       : 'source',
            'environ'   : 'BOT_SOURCE'
        },
        {
            'key'       : 'maxage',
            'environ'   : 'BOT_MAXAGE'
        }
    ]
    
    # Read configuration options from environment.
    for option in config_options:
        value = environ.get(option['environ'], None)
        
        if value:
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

def get_tweet(api, config):
    """Get tweet to which to reply"""
    
    candidate = get_latest_candidate_tweet(api, config)
    
    print_tweet(candidate)
    
    if not candidate:
        return None
    else:
        return tweet    
    
def print_tweet(tweet):
    if not tweet:
        print('No tweet')
    else:
        print('.  Tweet ID: ' + tweet.id_str)
        print('.  Created:  ' + str(tweet.created_at))
        print('.  Author:   ' + tweet.author.screen_name)
        print('.  ' + tweet.text)

def handler(event, context):
    """Aws Lambda Function handler."""
    
    config      = load_configuration()
    api         = instanciate_api(config)
    candidate   = get_latest_candidate_tweet(api, config)
    
    print_tweet(candidate)

def main(argv):

    config      = load_configuration()
    api         = instanciate_api(config)
    candidate   = get_latest_candidate_tweet(api, config)
    
    print_tweet(candidate)

if __name__ == '__main__':
    main(sys.argv)
