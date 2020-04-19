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

STACK=GoodBotBot
PACKAGE=goodbotbot.zip
DEPENDENCY_DIR=./target
DEPENDENDY_ZIP=target.zip

.PHONY: all
all: ${PACKAGE}

.PHONY: clean
clean:
	-rm -f ${DEPENDENDY_ZIP} ${PACKAGE}
	-rm -rf ${DEPENDENCY_DIR}

.PHONY: deploy
deploy: ${PACKAGE}
	aws lambda update-function-code \
		--function-name `aws cloudformation describe-stacks --stack-name=${STACK} --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text` \
		--zip-file fileb://${PACKAGE}

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

# Separate rule with separate .zip file so we don't have to re-install and re-zip
# the dependencies whenever we change the code.
${PACKAGE}: ${DEPENDENDY_ZIP} index.py Makefile
	cp ${DEPENDENDY_ZIP} ${PACKAGE}
    
	# Add code to package
	zip -g ${PACKAGE} index.py
