FROM node:14-alpine

WORKDIR /system-tests

RUN mkdir node_modules && \
  chmod 777 -R /system-tests && \
  apk update && \
  apk add bash

USER node

COPY package* ./
RUN npm ci

COPY ./ ./

ENTRYPOINT ./docker-entrypoint.sh
