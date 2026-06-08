#!/bin/bash
# Build and push Docker image to ECR

REGION="us-east-1"
ACCOUNT_ID="525881110696"
REPO_NAME="mask2former-training"
IMAGE_TAG="latest"
PROFILE="sagemaker"

FULL_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG"

# Create repo if not exists
aws ecr create-repository --repository-name "$REPO_NAME" --region "$REGION" --profile "$PROFILE" 2>/dev/null

# Login to ECR
aws ecr get-login-password --region "$REGION" --profile "$PROFILE" | \
    docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Login to DLC base image registry
aws ecr get-login-password --region "$REGION" --profile "$PROFILE" | \
    docker login --username AWS --password-stdin 763104351884.dkr.ecr.$REGION.amazonaws.com

# Build and push
docker build -t "$REPO_NAME" .
docker tag "$REPO_NAME:latest" "$FULL_URI"
docker push "$FULL_URI"

echo "Pushed: $FULL_URI"
