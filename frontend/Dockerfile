# Multi-stage production image for Next.js.
# Dev mode uses docker-compose.yml's `image: node:20-alpine` override, not this file.

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Inject runtime public env at build time (baked into JS bundle)
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8001/api/ws/live
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S next && adduser -S next -G next
COPY --from=builder --chown=next:next /app/.next ./.next
COPY --from=builder --chown=next:next /app/node_modules ./node_modules
COPY --from=builder --chown=next:next /app/package.json ./package.json
COPY --from=builder --chown=next:next /app/public ./public
USER next
EXPOSE 3000
CMD ["npm", "start"]
