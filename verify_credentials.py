import boto3
from botocore.exceptions import ClientError

def verify_credentials():
    sts = boto3.client('sts')
    try:
        sts.get_caller_identity()
        return True
    except ClientError as e:
        print(f"Credentials are not valid: {e}")
        return False

def list_buckets():
    s3 = boto3.client('s3')
    response = s3.list_buckets()
    return [bucket['Name'] for bucket in response['Buckets']]

if __name__ == "__main__":
    if verify_credentials():
        buckets = list_buckets()
        print("S3 Buckets:", buckets)
    else:
        print("Invalid AWS credentials.")
