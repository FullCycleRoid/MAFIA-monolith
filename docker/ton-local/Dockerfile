FROM node:18-slim

WORKDIR /app

# Копируем package.json и устанавливаем зависимости
COPY package.json ./
RUN npm install

# Копируем сервер
COPY ton-mock-server.js ./

EXPOSE 8081 8082

CMD ["node", "ton-mock-server.js"]