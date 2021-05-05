FROM node:14-alpine AS environment
WORKDIR /document-store-worker
RUN apk update && \
  apk update && \
  apk add git bash make gcc g++ python3 python3-dev && \
  mkdir -pv /document-store-worker/dist/bundle  && \
  chmod -Rv 777 /document-store-worker
USER node
COPY package* ./
RUN npm ci
COPY ./ ./
ENTRYPOINT ["./dev.docker-entrypoint.sh"]


FROM environment AS build
RUN npm run build && cp prod.docker-entrypoint.sh dist/bundle/prod.docker-entrypoint.sh



FROM node:14-alpine AS production
WORKDIR /document-store-worker
COPY --from=build /document-store-worker/dist/bundle ./
ENTRYPOINT ["./prod.docker-entrypoint.sh"]
CMD ["--help"]
