# Сборка интерфейса — Node, затем статику раздаёт nginx.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
# npm ci требует ровно совпадающий package-lock.json, а его в репозитории нет,
# поэтому ставим зависимости без сверки снимка.
RUN npm install
COPY . .
RUN npm run build

# nginx отдаёт dist и проксирует /api на backend:8000 (см. nginx.conf).
# Раньше здесь был "serve": у него нет проксирования, и запросы /api/* в рабочем
# режиме завершались 404.
FROM nginx:1.27-alpine AS runner
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]