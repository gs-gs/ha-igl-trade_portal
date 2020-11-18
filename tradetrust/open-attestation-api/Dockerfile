FROM node:alpine

WORKDIR /open-attestation-api

RUN apk update && apk update && apk add bash make git python3 g++ zip && chmod 777 /open-attestation-api

USER node

COPY package* ./
RUN npm ci
COPY ./ ./

ENTRYPOINT ./docker-entrypoint.sh
