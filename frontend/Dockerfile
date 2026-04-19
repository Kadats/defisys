FROM node:20-bookworm-slim
WORKDIR /app
COPY --chown=node:node package*.json ./
RUN npm ci --no-audit --no-fund
COPY --chown=node:node . .
USER node
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--webpack"]
