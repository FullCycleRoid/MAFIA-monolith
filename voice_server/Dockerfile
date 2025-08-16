FROM node:18-slim

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
CMD ["node", "server.js"]

EXPOSE 4443
EXPOSE 30000-30010/udp
