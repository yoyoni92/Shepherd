FROM ollama/ollama:latest

ARG OLLAMA_MODEL=llama3

# Start server, pull model, stop server - weights baked into this layer.
RUN ollama serve & \
    sleep 5 && \
    ollama pull ${OLLAMA_MODEL} && \
    pkill ollama || true

EXPOSE 11434
ENTRYPOINT ["/bin/ollama"]
CMD ["serve"]
