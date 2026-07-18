import boto3
from datetime import datetime, timedelta, timezone
import csv
import io
import random
import json
from botocore.exceptions import ClientError

ce = boto3.client('ce', region_name='us-east-1')
s3 = boto3.client('s3')
BUCKET = 'my-cost-dashboard-doreen'

# Services to generate mock costs for
SERVICES = ['Amazon EC2', 'Amazon S3', 'AWS Lambda', 'Amazon CloudFront', 'Amazon RDS', 'Amazon DynamoDB', 'AWS Data Transfer']

def lambda_handler(event, context):
    if 'startDate' in event and 'endDate' in event:
        start = event['startDate']
        end = event['endDate']
        end_exclusive = (datetime.fromisoformat(end) + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        start = yesterday.strftime('%Y-%m-%d')
        end_exclusive = (yesterday + timedelta(days=1)).strftime('%Y-%m-%d')

    # Generate a list of all dates in the range
    current = datetime.fromisoformat(start)
    end_date = datetime.fromisoformat(end_exclusive)
    dates = []
    while current < end_date:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    for day in dates:
        rows = []
        total = 0.0
        for service in SERVICES:
            # Random daily cost between $0.50 and $5.00
            amount = round(random.uniform(0.5, 5.0), 4)
            rows.append([service, amount])
            total += amount
        rows.append(['Total', round(total, 4)])

        # Write CSV to S3
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['Service', 'Cost'])
        writer.writerows(rows)

        s3_key = f'raw/{day}.csv'
        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=csv_buffer.getvalue())
        print(f"Saved {day} - ${total:.2f}")

    # Update manifest.json so the dashboard knows which files exist
    try:
        existing = s3.get_object(Bucket=BUCKET, Key='raw/manifest.json')
        manifest = set(json.loads(existing['Body'].read()))
    except ClientError as e:
        print(f"manifest.json not found or inaccessible: {e.response['Error']['Code']}")
        manifest = set()

    manifest.update(dates)
    s3.put_object(
        Bucket=BUCKET,
        Key='raw/manifest.json',
        Body=json.dumps(sorted(manifest)),
        ContentType='application/json'
    )

    return {'statusCode': 200, 'body': f'Processed {len(dates)} day(s) with mock data'}
