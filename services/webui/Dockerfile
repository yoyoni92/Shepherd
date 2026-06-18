FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* vars are inlined at build time
ARG NEXT_PUBLIC_FLEET_API_URL=http://fleet-api:8000
ARG NEXT_PUBLIC_AGENT_URL=http://langgraph-agent:8000
ARG NEXT_PUBLIC_RAG_URL=http://rag:8000
ARG NEXT_PUBLIC_GATEWAY_URL=http://channel-gateway:8000
ARG NEXT_PUBLIC_ASSISTANT_URL=http://ollama-assistant:8000
ENV NEXT_PUBLIC_FLEET_API_URL=$NEXT_PUBLIC_FLEET_API_URL
ENV NEXT_PUBLIC_AGENT_URL=$NEXT_PUBLIC_AGENT_URL
ENV NEXT_PUBLIC_RAG_URL=$NEXT_PUBLIC_RAG_URL
ENV NEXT_PUBLIC_GATEWAY_URL=$NEXT_PUBLIC_GATEWAY_URL
ENV NEXT_PUBLIC_ASSISTANT_URL=$NEXT_PUBLIC_ASSISTANT_URL
RUN mkdir -p public && npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
