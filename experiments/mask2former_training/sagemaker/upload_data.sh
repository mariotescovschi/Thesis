#!/bin/bash
# Upload dataset to S3 for SageMaker training
# Run after build_dataset.py completes

BUCKET="qwen3vl-floorplan-training-525881"
PREFIX="mask2former/data"
DATASET_DIR="$HOME/Projects/Facultate/Licenta/dataset"
CUBICASA_DIR="$HOME/Downloads/cubicasa5k"

echo "Uploading JSON annotations..."
aws s3 cp "$DATASET_DIR/train.json" "s3://$BUCKET/$PREFIX/train.json" --profile sagemaker
aws s3 cp "$DATASET_DIR/val.json" "s3://$BUCKET/$PREFIX/val.json" --profile sagemaker

echo "Syncing images (this will take a while)..."
aws s3 sync "$CUBICASA_DIR" "s3://$BUCKET/$PREFIX/images/" \
    --profile sagemaker \
    --exclude "*" \
    --include "*/F1_scaled.png" \
    --include "*/model.svg"

echo "Done. Data at s3://$BUCKET/$PREFIX/"
