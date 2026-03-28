FROM alpine:3.22 AS python-builder
RUN apk add --no-cache python3

FROM n8nio/n8n:latest
USER root
COPY --from=python-builder /usr/bin/python3 /usr/bin/python3
COPY --from=python-builder /usr/lib/python3* /usr/lib/
COPY --from=python-builder /usr/lib/libpython3* /usr/lib/
USER node
