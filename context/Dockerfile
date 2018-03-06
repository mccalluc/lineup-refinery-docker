FROM node:9.7.1 AS build
ENV REPO=lineup
RUN git clone https://github.com/mccalluc/$REPO.git
WORKDIR $REPO/
RUN git checkout v0.0.1  # on "taggle" branch
RUN npm install
RUN npm run build


FROM nginx:1.13.9-alpine AS deploy
COPY --from=build /lineup/build /usr/share/nginx/html
