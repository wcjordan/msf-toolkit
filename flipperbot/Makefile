#!make

# Build container
.PHONY: build
build:
	DOCKER_BUILDKIT=1 docker build -t flipperbot:latest .

# Run container
.PHONY: start
start:
	docker run --rm flipperbot:latest

