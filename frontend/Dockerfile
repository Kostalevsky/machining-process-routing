# build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json /app/
COPY frontend/package-lock.json /app/
RUN npm ci
# Копируем только исходники, исключая node_modules
COPY frontend/src /app/src
COPY frontend/index.html /app/
COPY frontend/vite.config.ts /app/
COPY frontend/tailwind.config.cjs /app/
COPY frontend/postcss.config.cjs /app/
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

# serve stage
FROM nginx:alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx","-g","daemon off;"]
