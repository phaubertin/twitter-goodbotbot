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

# Deployment package for AWS Lambda function: final packaged code and
# dependencies.
PACKAGE=goodbotbot.zip

# Packaged dependencies without the code. Having a separate zip file for the
# dependencies speeds up the build when only the code, not the dependencies
# has changed.
DEPENDENCY_DIR=./target
DEPENDENDY_ZIP=target.zip

# Name of the virtual Python environment for running locally (poll target). The
# virtual environment is not involved in any way when building the deployment
# package.
PYTHON_VENV=venv

# The presence of this file indicates the virtual environment is completely
# configured. Its modified time checked against the one for requirements.txt
# allows make to confirm that the virtual environment is up to date.
PYTHON_VENV_FILE=${PYTHON_VENV}/uptodate.txt

# Target-specific configuration files (poll and push targets).
POLL_CONFIG=poll.conf.sh
PUSH_CONFIG=push.conf.sh

# This is the default target. It builds the AWS Lambda deployment package that
# contains the application code and its dependencies.
.PHONY: all
all: ${PACKAGE}

# Cleanup target.
.PHONY: clean
clean:
	-rm -f ${DEPENDENDY_ZIP} ${PACKAGE} ${PYTHON_VENV_FILE}
	-rm -rf ${DEPENDENCY_DIR} ${PYTHON_VENV}

.PHONY: distclean
distclean: clean
	-rm -f ${POLL_CONFIG} ${PUSH_CONFIG}

# This target updates the code running in AWS Lambda. It works if the following
# conditions are met:
#   1) The application has been deployed using the provided CloudFormation
#      template:
#           cloudformation/goodbotbot.json
#   2) The AWS Command line Interface (CLI) is installed:
#           https://aws.amazon.com/cli/
#   3) The AWS Command line Interface (CLI) is configured correctly, with
#      credentials.
#   4) The user identified by the credentials with which the AWS CLI is
#      configured has permissions to update the code of the AWS Lambda function.
#      For convenience, the CloudFormation stack creates an IAM managed policy
#      (resource name LambdaDeployManagedPolicy) that you can simply attach to
#      your IAM user to give it the correct permissions.
#
# The first time you run this target, you are prompted for the name of your
# CloudFormation stack and for the AWS region in which it resides. This
# information is remembered in configuration file ${PUSH_CONFIG}.
.PHONY: push
push: ${PACKAGE} push.conf.sh
	(source ./${PUSH_CONFIG}; \
	aws lambda update-function-code \
		--region=$$REGION \
        --function-name `aws cloudformation describe-stacks --region=$$REGION --stack-name=$$STACK \
                --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text` \
		--zip-file fileb://${PACKAGE} | grep -v VARIABLES)

${PUSH_CONFIG}:
	./config.sh push $@

# This targets runs the code locally to check if there is a new tweet that has
# not yet been replied to. Output is the same as the log output of the AWS
# Lambda function, but his will not send any tweet or check periodically. This
# is a punctual check.
#
# The first time you run this target, you are prompted for configuration
# information including the required Twitter credentials. This information is
# remembered in the file ${POLL_CONFIG}.
#
# The  first time you run this target, the Python virtual environment is built,
# which takes about a minute. Python packages are downloaded as needed.
.PHONY: poll
poll: ${POLL_CONFIG} venv
	(source ./${POLL_CONFIG}; \
	 ${PYTHON_VENV}/bin/python index.py)

${POLL_CONFIG}:
	./config.sh poll $@
    
.PHONY: venv
venv: ${PYTHON_VENV_FILE}

${PYTHON_VENV_FILE}: requirements.txt
	virtualenv ${PYTHON_VENV}
	${PYTHON_VENV}/bin/python -m pip install -r requirements.txt
	touch $@

# This target builds the dependency package. Python packages are downloaded as
# needed.
${DEPENDENDY_ZIP}: requirements.txt
	# Delete existing dependencies
	rm -f ${DEPENDENDY_ZIP}
	rm -rf ${DEPENDENCY_DIR}

	# Install dependencies
	python3 -m pip install --target ${DEPENDENCY_DIR} -r requirements.txt

	# Remove packages provided by the AWS Lambda runtime to make the deployment
	# package smaller. The botocore package by itself makes over half the size of
	# the deployment package.
	#
	# For reference, this is the output of "pip list" on an AWS Lambda function
	# using the Python 3.7 run time (I could not find this documented anywhere):
	#
	# Package         Version
	# --------------- -------
	# boto3           1.12.22
	# botocore        1.15.22
	# docutils        0.15.2 
	# jmespath        0.9.5  
	# pip             19.2.3 
	# python-dateutil 2.8.1  
	# s3transfer      0.3.3  
	# setuptools      41.2.0 
	# six             1.14.0 
	# urllib3         1.25.8 
	rm -rf ${DEPENDENCY_DIR}/botocore*
	rm -rf ${DEPENDENCY_DIR}/docutils*
	rm -rf ${DEPENDENCY_DIR}/jmespath*
	rm -rf ${DEPENDENCY_DIR}/six*
	rm -rf ${DEPENDENCY_DIR}/urllib3*

	# Remove __pycache__ because it contains stuff from the packages we just
	# removed.
	rm -rf ${DEPENDENCY_DIR}/__pycache__

	# Zip package
	(cd ${DEPENDENCY_DIR} && zip -r ${DEPENDENDY_ZIP} .)
	mv ${DEPENDENCY_DIR}/${DEPENDENDY_ZIP} .

# Separate rule with separate .zip file so we don't have to re-install and
# re-zip the dependencies whenever we change the code.
${PACKAGE}: ${DEPENDENDY_ZIP} index.py Makefile
	cp ${DEPENDENDY_ZIP} ${PACKAGE}
    
	# Add code to package
	zip -g ${PACKAGE} index.py
