from aws_cdk import (
    Stack,
    TimeZone,
    aws_lambda as _lambda,
    aws_dynamodb as _dynamodb,
    aws_s3 as _s3,
    aws_apigateway as _apigateway,
    aws_scheduler_targets as _targets,
    aws_iam as _iam,
    RemovalPolicy,
    Duration,
)
from aws_cdk.aws_scheduler import Schedule, ScheduleExpression, ScheduleTargetInput
from constructs import Construct

class EccInterviewStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Table to store items
        table = _dynamodb.Table(
            self,
            "Items",
            partition_key=_dynamodb.Attribute(name="id", type=_dynamodb.AttributeType.STRING),
            billing_mode=_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Bucket to store reports
        bucket = _s3.Bucket(
            self,
            "Reports",
            block_public_access=_s3.BlockPublicAccess.BLOCK_ALL,
            encryption=_s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
                auto_delete_objects=True,
        )

        # Lambda function to ingest items into DynamoDB
        ingest_role = _iam.Role(
            self,
            "IngestRole",
            assumed_by=_iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        ingest_role.add_to_policy(
            _iam.PolicyStatement(
                actions=["dynamodb:PutItem"],
                resources=[table.table_arn],
            )
        )

        # Lambda function to generate reports and store them in S3
        report_role = _iam.Role(
            self,
            "ReportRole",
            assumed_by=_iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        report_role.add_to_policy(
            _iam.PolicyStatement(
                actions=["s3:PutObject"],
                resources=[bucket.arn_for_objects("*")],
            )
        )

        report_role.add_to_policy(
            _iam.PolicyStatement(
                actions=["dynamodb:Scan"],
                resources=[table.table_arn],
            )
        )

        # Lambda function to ingest items into DynamoDB
        fnIngest = _lambda.Function(
            self, "IngestFunction",
            runtime = _lambda.Runtime.PYTHON_3_12,
            handler = "handler.handler",
            role=ingest_role,
            code = _lambda.Code.from_asset("src/lambdas/ingest"),
            environment={
                "TABLE_NAME": table.table_name
            }
        )

        # Lambda function to generate reports and store them in S3
        fnReport = _lambda.Function(
            self, "ReportFunction",
            runtime = _lambda.Runtime.PYTHON_3_12,
            handler = "handler.handler",
            role=report_role,
            code = _lambda.Code.from_asset("src/lambdas/report"),
            timeout=Duration.minutes(5),
            environment={
                "TABLE_NAME": table.table_name,
                "BUCKET_NAME": bucket.bucket_name
            }
        )

        # Ingest API Gateway
        api = _apigateway.LambdaRestApi(self, "ingest-api",
            handler=fnIngest,
            proxy=False
        )

        items = api.root.add_resource("items")
        items.add_method("POST")

        # Lambda Reports Triggered by Scheduler
        target = _targets.LambdaInvoke(fnReport,
            input=ScheduleTargetInput.from_object({
                "payload": "useful"
            })
        )

        Schedule(self, "Schedule",
            schedule=ScheduleExpression.cron(
                minute="0",
                hour="23",
                week_day="7",
                time_zone=TimeZone.EUROPE_LISBON
            ),
            target=target,
            description="Trigger the report lambda every Saturday at 11 PM Europe/Lisbon"
        )