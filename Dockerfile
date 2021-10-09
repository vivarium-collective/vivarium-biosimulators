# BioSimulator dockerfiles can be found here: https://github.com/biosimulators/Biosimulators
# set base image
FROM ghcr.io/biosimulators/biosimulators

# copy vivarium-simulators to working dir
COPY . /app

# install dependencies
## biosimulators test suite for examples
RUN git clone https://github.com/biosimulators/Biosimulators_test_suite.git
RUN pip install Biosimulators_test_suite
## vivarium-biosimulators requirements
RUN pip install vivarium-core
# RUN pip install -r requirements.txt
run pip install -r update_requirements.txt --upgrade

# start mock up server for output
# RUN pipenv run xvfb-startup.sh

# command
CMD ["python", "vivarium_biosimulators/experiments/test_biosimulators.py", "-e", "0"]
