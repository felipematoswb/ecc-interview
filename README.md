# ECC Interview

Python AWS CDK application that receives items through API Gateway, stores them
in DynamoDB, and generates weekly reports in S3.

## Prerequisites

- Python 3.12 or later
- Node.js and the AWS CDK CLI (`npm install -g aws-cdk`)
- AWS CLI configured with credentials and permissions to create the stack resources

## Local development

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
```

On Windows, activate the environment with:

```bat
.venv\Scripts\activate.bat
```

Run synthesize the CloudFormation template:

```bash
cdk synth
```

This project does not configure a local emulator for API Gateway, DynamoDB, or
S3. `pytest` and `cdk synth` can validate the code and infrastructure locally,
but the stack must be deployed to AWS to send real requests.

## Deploy to AWS

Configure the AWS profile and region to use (for example, with `aws configure`)
and bootstrap the account and region once:

```bash
cdk bootstrap
```

Review the changes and deploy the stack:

```bash
cdk diff
cdk deploy EccInterviewStack
```

After deployment, find the API invoke URL in the AWS console under
**API Gateway → APIs → ingest-api → Stages → prod**. Use this URL as `API_URL`
in the examples below. The ingestion resource is `/items`.

## Submit an item

Set the invoke URL and send a JSON object:

```bash
export API_URL="https://<api-id>.execute-api.<region>.amazonaws.com/prod"

curl -X POST "${API_URL}/items" \
  -H "Content-Type: application/json" \
  -d '{"name":"Example item"}'
```

An accepted request returns HTTP `201` with the item's `id`. The function also
stores `created_at`, derived from the request time and represented in the
`Europe/Lisbon` time zone. A request body that is not valid JSON returns HTTP
`400`.

## Reports

EventBridge Scheduler invokes the report function every Saturday at 11:00 PM in
the `Europe/Lisbon` time zone. Reports are saved in the stack's S3 bucket under
the `weekly/` prefix. Each report includes records from the previous Saturday
at 11:00 PM through the execution time, so a manual run during the week
includes records created since the most recent Saturday.

Deployment does not run the report immediately. To test it without waiting
until the next Saturday, find `ReportFunction` in the stack's CloudFormation
resources and select **Test** in the Lambda console with the `{}` event. Then
look in the `Reports` bucket for an object named
`weekly/report_YYYY-MM-DD.json`. If the function fails, check its logs in
CloudWatch Logs.

## Useful commands

- `cdk ls`: list the stacks
- `cdk synth`: synthesize the CloudFormation template
- `cdk diff`: compare the local stack with the deployed one
- `cdk deploy`: deploy the stack
- `cdk destroy`: remove the stack from AWS
