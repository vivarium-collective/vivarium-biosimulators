# set base image
FROM ghcr.io/biosimulators/biosimulators@sha256:0b712cef599bc0b9cfbe5c4d0abbd7aad55d71ad7d5f74407ab1e44c64ef1754

# set working dir
COPY . /app
# WORKDIR /app

# install dependencies
RUN pipenv run pip install -r requirements.txt
RUN pipenv run pip install -r simulator_requirements.txt --upgrade

# start mock up server for output
# RUN pipenv run xvfb-startup.sh

# command
CMD "pipenv run python vivarium_biosimulators/processes/biosimulators_process.py"
