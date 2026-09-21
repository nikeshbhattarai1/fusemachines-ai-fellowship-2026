# Local vLLM Deployment

## Model
The local fallback serves Meta-Llama-3-8B-Instruct through the OpenAI-compatible vLLM server on port 8001.

## Resource settings
The server runs with a maximum model length of 8192 tokens and a GPU memory utilization of 0.90.

## Requirements
An NVIDIA GPU with the nvidia-container-toolkit is required. The service is optional and only starts with the Docker Compose profile named gpu.
