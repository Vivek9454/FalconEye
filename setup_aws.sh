#!/bin/bash

# FalconEye AWS S3 Setup Script
# This script helps you configure AWS credentials securely

echo "🔧 FalconEye AWS S3 Setup"
echo "========================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   brew install awscli"
    echo "   or visit: https://aws.amazon.com/cli/"
    exit 1
fi

echo "✅ AWS CLI found"
echo ""

# Check if already configured
if aws configure list | grep -q "access_key"; then
    echo "🔍 Found existing AWS configuration:"
    aws configure list
    echo ""
    read -p "Do you want to use existing credentials? (y/n): " use_existing
    
    if [[ $use_existing == "y" || $use_existing == "Y" ]]; then
        echo "✅ Using existing AWS credentials"
        echo ""
        echo "To use these credentials with FalconEye, run:"
        echo "export AWS_ACCESS_KEY_ID=\$(aws configure get aws_access_key_id)"
        echo "export AWS_SECRET_ACCESS_KEY=\$(aws configure get aws_secret_access_key)"
        echo "export AWS_DEFAULT_REGION=ap-south-1"
        echo ""
        echo "Then restart FalconEye:"
        echo "pkill -f python; source venv/bin/activate && python backend.py"
        exit 0
    fi
fi

echo "🔑 Setting up new AWS credentials..."
echo ""

# Get AWS credentials
read -p "Enter AWS Access Key ID: " aws_access_key
read -s -p "Enter AWS Secret Access Key: " aws_secret_key
echo ""
read -p "Enter AWS Region (default: ap-south-1): " aws_region
aws_region=${aws_region:-ap-south-1}

# Validate credentials
echo ""
echo "🧪 Testing AWS credentials..."

export AWS_ACCESS_KEY_ID="$aws_access_key"
export AWS_SECRET_ACCESS_KEY="$aws_secret_key"
export AWS_DEFAULT_REGION="$aws_region"

if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials are valid!"
    echo ""
    echo "🔧 To use these credentials with FalconEye, add to your shell profile:"
    echo "export AWS_ACCESS_KEY_ID=\"$aws_access_key\""
    echo "export AWS_SECRET_ACCESS_KEY=\"$aws_secret_key\""
    echo "export AWS_DEFAULT_REGION=\"$aws_region\""
    echo ""
    echo "Or run this command now:"
    echo "export AWS_ACCESS_KEY_ID=\"$aws_access_key\" && export AWS_SECRET_ACCESS_KEY=\"$aws_secret_key\" && export AWS_DEFAULT_REGION=\"$aws_region\""
    echo ""
    echo "Then restart FalconEye:"
    echo "pkill -f python; source venv/bin/activate && python backend.py"
else
    echo "❌ AWS credentials are invalid. Please check your credentials and try again."
    exit 1
fi
