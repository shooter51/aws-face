import boto3
from botocore.exceptions import ClientError
import re

def sanitize_image_key(image_key):
    return re.sub(r'[^a-zA-Z0-9_.\-:]', '_', image_key)

def verify_credentials():
    sts = boto3.client('sts')
    try:
        sts.get_caller_identity()
        return True
    except ClientError as e:
        print(f"Credentials are not valid: {e}")
        return False

def list_images(bucket_name):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    operation_parameters = {'Bucket': bucket_name}
    page_iterator = paginator.paginate(**operation_parameters)

    image_files = []
    for page in page_iterator:
        if 'Contents' in page:
            for obj in page['Contents']:
                if obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(obj['Key'])
    return image_files

def create_collection_if_not_exists(collection_id):
    rekognition = boto3.client('rekognition')
    try:
        rekognition.describe_collection(CollectionId=collection_id)
        print(f"Collection {collection_id} already exists.")
    except rekognition.exceptions.ResourceNotFoundException:
        rekognition.create_collection(CollectionId=collection_id)
        print(f"Collection {collection_id} created.")

def detect_faces(bucket_name, image_key):
    rekognition = boto3.client('rekognition')
    response = rekognition.detect_faces(
        Image={'S3Object': {'Bucket': bucket_name, 'Name': image_key}},
    )
    return response['FaceDetails']

def is_image_indexed(collection_id, image_key):
    rekognition = boto3.client('rekognition')
    try:
        response = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={'S3Object': {'Bucket': bucket_name, 'Name': image_key}},
            MaxFaces=1
        )
        return len(response['FaceMatches']) > 0
    except rekognition.exceptions.InvalidParameterException:
        return False

def move_image_to_bucket(source_bucket, image_key, destination_bucket):
    s3 = boto3.client('s3')
    copy_source = {'Bucket': source_bucket, 'Key': image_key}
    s3.copy(copy_source, destination_bucket, image_key)
    s3.delete_object(Bucket=source_bucket, Key=image_key)
    print(f"Moved {image_key} from {source_bucket} to {destination_bucket}")

def index_faces(bucket_name, image_key, collection_id, no_faces_bucket):
    if is_image_indexed(collection_id, image_key):
        print(f"Image {image_key} is already indexed.")
        return []
    rekognition = boto3.client('rekognition')
    sanitized_key = sanitize_image_key(image_key)
    response = rekognition.index_faces(
        CollectionId=collection_id,
        Image={'S3Object': {'Bucket': bucket_name, 'Name': image_key}},
        ExternalImageId=sanitized_key,
        DetectionAttributes=['ALL']
    )
    if not response['FaceRecords']:
        move_image_to_bucket(bucket_name, image_key, no_faces_bucket)
    return response['FaceRecords']

if __name__ == "__main__":
    if verify_credentials():
        bucket_name = input("Enter the S3 bucket name: ")
        collection_id = input("Enter the Rekognition collection ID: ")
        no_faces_bucket = input("Enter the bucket name for images with no faces: ")
        create_collection_if_not_exists(collection_id)
        images = list_images(bucket_name)
        print(f"Found {len(images)} images in the bucket.")
        for image in images:
            print(image)
            face_records = index_faces(bucket_name, image, collection_id, no_faces_bucket)
            print(f"Indexed {len(face_records)} faces in {image}.")
    else:
        print("Invalid AWS credentials.")