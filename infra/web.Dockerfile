FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
COPY apps/api/package.json apps/api/package.json
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web
ENV NEXT_PUBLIC_API_URL=http://localhost:3001
RUN npm run build -w @unified/web
EXPOSE 3000
CMD ["npm", "run", "start", "-w", "@unified/web"]
