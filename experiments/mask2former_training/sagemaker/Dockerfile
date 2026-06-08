FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.4.0-gpu-py311-cu124-ubuntu22.04-sagemaker

RUN pip install --no-cache-dir \
    opencv-python-headless \
    pycocotools \
    timm \
    scipy

# Detectron2 from source
RUN pip install --no-cache-dir "git+https://github.com/facebookresearch/detectron2.git"

# Clone Mask2Former (CUDA ops built at runtime since CodeBuild has no GPU)
RUN git clone https://github.com/facebookresearch/Mask2Former.git /opt/ml/code/Mask2Former

ENV PYTHONUNBUFFERED=1
WORKDIR /opt/ml

COPY train.py /opt/ml/code/train.py

ENTRYPOINT ["python3", "/opt/ml/code/train.py"]
