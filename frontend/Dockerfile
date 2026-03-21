# Тот же контент, что node:20-alpine; тянется не через docker.io (см. корневой Dockerfile).
FROM public.ecr.aws/docker/library/node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

RUN chmod +x node_modules/.bin/* || true
RUN npm run build

FROM public.ecr.aws/docker/library/nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

