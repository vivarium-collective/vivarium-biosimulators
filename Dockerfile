# BioSimulator dockerfiles can be found here: https://github.com/biosimulators/Biosimulators
# set base image
FROM ghcr.io/biosimulators/biosimulators@sha256:0b712cef599bc0b9cfbe5c4d0abbd7aad55d71ad7d5f74407ab1e44c64ef1754

# copy vivarium-simulators to working dir
COPY . /app

# install dependencies
## biosimulators test suite for examples
RUN pipenv run git clone https://github.com/biosimulators/Biosimulators_test_suite.git
RUN pipenv run pip install Biosimulators_test_suite
## vivarium-biosimulators requirements
RUN pipenv run pip install -r requirements.txt
RUN pipenv run pip install -r update_requirements.txt --upgrade

# start mock up server for output
# RUN pipenv run xvfb-startup.sh

# command
CMD ["pipenv", "run", "python", "vivarium_biosimulators/experiments/test_biosimulators.py"]
