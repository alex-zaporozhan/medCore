# Default: docker.io (works with standard daemon/proxy). Override if needed:
#   docker build --build-arg NODE_IMAGE=public.ecr.aws/docker/library/node:20-alpine -t dental-booking-frontend:local .
ARG NODE_IMAGE=node:20-alpine
FROM ${NODE_IMAGE} AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

RUN chmod +x node_modules/.bin/* || true
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

