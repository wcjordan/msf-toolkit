#!make

# Build container
.PHONY: build
build:
	DOCKER_BUILDKIT=1 docker build -t gcr.io/flipperkid-default/msf-toolkit-bot:latest flipperbot

# Run container
.PHONY: start
start:
	docker run --rm gcr.io/flipperkid-default/msf-toolkit-bot:latest

# Deploy
.PHONY: deploy
deploy:
	docker push gcr.io/flipperkid-default/msf-toolkit-bot:latest
	helm upgrade --install msf-toolkit helm
	cd war_breakdown_extraction/src; gcloud functions deploy extract_war_breakdown \
		--runtime python38 --trigger-bucket war_roster_screenshots.msf.flipperkid.com
