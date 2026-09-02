ARG NODE_IMAGE=public.ecr.aws/docker/library/node:20-alpine
ARG NGINX_IMAGE=public.ecr.aws/docker/library/nginx:1.27-alpine
FROM ${NODE_IMAGE} AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
ARG VITE_CAMCAT_API_BASE=
ARG VITE_CAMCAT_USER_ID=camcat-local-user
ENV VITE_CAMCAT_API_BASE=$VITE_CAMCAT_API_BASE \
    VITE_CAMCAT_USER_ID=$VITE_CAMCAT_USER_ID
RUN npm run build

FROM ${NGINX_IMAGE}
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
