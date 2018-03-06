FROM node:9.7.1 AS build
ENV REPO=lineup
RUN git clone https://github.com/Caleydo/$REPO.git
WORKDIR $REPO/
RUN git checkout 53b52eb7b7e3f969e4d9c2c5c2ddb227429724c0  # Latest commit on "taggle" branch
RUN npm install
RUN npm run build
