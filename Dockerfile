# set base image
FROM ghcr.io/biosimulators/biosimulators@sha256:0b712cef599bc0b9cfbe5c4d0abbd7aad55d71ad7d5f74407ab1e44c64ef1754

# set working dir
COPY . /code
WORKDIR /code

# install dependencies
RUN python -m pip install --upgrade pip
RUN pip install -r /code/requirements.txt
