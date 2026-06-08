"""Launch Mask2Former training on SageMaker (L40S 48GB)."""
import boto3
import time
import os
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_REGION", "us-east-1")
ACCOUNT_ID = "525881110696"
ROLE_ARN = os.environ["SAGEMAKER_ROLE"]
S3_BUCKET = "qwen3vl-floorplan-training-525881"

IMAGE_URI = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/mask2former-training:latest"
JOB_NAME = f"mask2former-floorplan-{int(time.time())}"

session = boto3.Session(profile_name="sagemaker", region_name=REGION)
sm = session.client("sagemaker")

response = sm.create_training_job(
    TrainingJobName=JOB_NAME,
    AlgorithmSpecification={"TrainingImage": IMAGE_URI, "TrainingInputMode": "File"},
    RoleArn=ROLE_ARN,
    InputDataConfig=[{
        "ChannelName": "training",
        "DataSource": {
            "S3DataSource": {
                "S3DataType": "S3Prefix",
                "S3Uri": f"s3://{S3_BUCKET}/mask2former/data/",
                "S3DataDistributionType": "FullyReplicated",
            }
        },
    }],
    OutputDataConfig={"S3OutputPath": f"s3://{S3_BUCKET}/mask2former/output/"},
    ResourceConfig={
        "InstanceType": "ml.g6e.2xlarge",  # 1x L40S 48GB
        "InstanceCount": 1,
        "VolumeSizeInGB": 200,
    },
    StoppingCondition={"MaxRuntimeInSeconds": 36000},  # 10h max
)

print(f"Job started: {JOB_NAME}")
print(f"Instance: ml.g6e.2xlarge (1x L40S 48GB)")
print(f"Monitor: https://console.aws.amazon.com/sagemaker/home?region={REGION}#/jobs/{JOB_NAME}")
