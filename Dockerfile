# set base image
FROM ghcr.io/biosimulators/biosimulators@sha256:0b712cef599bc0b9cfbe5c4d0abbd7aad55d71ad7d5f74407ab1e44c64ef1754

# # set working dir
# COPY . /code
# WORKDIR /code

# install dependencies
# RUN pipenv install --selective-upgrade pip
RUN pipenv run pip install -r requirements.txt
# RUN pipenv run pip install setup.py

# start mock up server for output
#     "/bin/bash", "/xvfb-startup.sh",
CMD "pipenv run python vivarium_biosimulators/processes/biosimulators_process.py"
