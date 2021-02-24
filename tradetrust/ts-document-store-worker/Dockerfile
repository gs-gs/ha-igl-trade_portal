FROM node:14-alpine

WORKDIR /document-store-worker

RUN apk update && apk update && apk add git bash make gcc g++ python3 python3-dev && chmod 777 /document-store-worker

USER node

COPY package* ./
RUN npm ci
COPY ./ ./

ENTRYPOINT ./docker-entrypoint.sh
