# set base image
FROM ghcr.io/biosimulators/biosimulators@sha256:0b712cef599bc0b9cfbe5c4d0abbd7aad55d71ad7d5f74407ab1e44c64ef1754

# set working dir
COPY . /code
# WORKDIR /code

# install dependencies
# RUN pipenv install --selective-upgrade pip
# RUN pipenv run pip install -r /code/requirements.txt
RUN pipenv run pip install /code/setup.py

# start up mock up server for output
#     "/bin/bash", "/xvfb-startup.sh",
CMD "/bin/bash pipenv run python /code/vivarium_biosimulators/processes/biosimulators_process.py"
