import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

interface EcsStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  repository: ecr.Repository;
}

export class EcsStack extends cdk.Stack {
  // Exposed so FrontendStack can point CloudFront at the ALB
  public readonly albDnsName: string;

  constructor(scope: Construct, id: string, props: EcsStackProps) {
    super(scope, id, props);
    const { vpc, repository } = props;

    // Logging (Essential especailly when an app is like this is split into microservices)
    const logGroup = new logs.LogGroup(this, "BackendLogs", {
      logGroupName: "/iot-dashboard/backend",
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Cluster
    const cluster = new ecs.Cluster(this, "Cluster", {
      vpc,
      clusterName: "iot-dashboard",
      containerInsightsV2: ecs.ContainerInsights.ENABLED,
    });
    (cluster.node.defaultChild as cdk.CfnResource).applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);

    // IAM roles
    // Execution role: used by ECS control plane to pull the image + read secrets
    const executionRole = new iam.Role(this, "TaskExecutionRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AmazonECSTaskExecutionRolePolicy"
        ),
      ],
    });
    // Task role: runtime permissions for the application process 
    // A good way to reduce prompt injection too
    const taskRole = new iam.Role(this, "TaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });
    // Bedrock: invoke any model — narrow the resource ARN if you want tighter scope
    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        resources: ["*"],
      })
    );

    // Choosing Fargate here as I cannot anticipate the customer load, and hence this is the safest and cheapest option
    // This way I get both less latency and cost (varies for use case)
    const taskDef = new ecs.FargateTaskDefinition(this, "TaskDef", {
      memoryLimitMiB: 512, // Considering 512 MB should be good enough Python + LangGraph (Especially with my intent validation node restricting usage)
      cpu: 256,
      executionRole,
      taskRole,
    });

    taskDef.addContainer("Backend", {
      image: ecs.ContainerImage.fromEcrRepository(repository, "latest"),
      portMappings: [{ containerPort: 8000 }],
      environment: {
        // Using Bedrock in production to handle privacy
        LLM_PROVIDER: "bedrock",
        BEDROCK_REGION: this.region,
        // Nova Lite requires no AWS Marketplace subscription — works in any fresh account out of the box.
        // To use Claude instead, enable model access in the Bedrock console and set this to:
        // "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        BEDROCK_MODEL_ID: "us.amazon.nova-lite-v1:0",
        // Ephemeral SQLite — data resets on each deploy (acceptable for this project)
        DATABASE_URL: "sqlite+aiosqlite:///./iot_dashboard.db",
        LOG_LEVEL: "INFO",
        MAX_AI_RETRIES: "3",
        // CloudFront sits in front of ALB so browser and API share the same origin
        // — CORS is effectively a no-op in prod, but keeping for local-dev fallback
        CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]',
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "backend",
        logGroup,
      }),
    });

    // Load balancer (Frankly, an overkill for this project, but wanted to build with best practices)
    const alb = new elbv2.ApplicationLoadBalancer(this, "Alb", {
      vpc,
      internetFacing: true,
    });
    (alb.node.defaultChild as cdk.CfnResource).applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);

    const listener = alb.addListener("HttpListener", {
      port: 80,
      open: true,
    });

    // Fargate service
    const service = new ecs.FargateService(this, "Service", {
      cluster,
      taskDefinition: taskDef,
      desiredCount: 1,
      assignPublicIp: false,
      // Auto-rollback if health checks fail during a deployment
      circuitBreaker: { rollback: true },
    });

    listener.addTargets("BackendTarget", {
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [service],
      healthCheck: {
        path: "/api/health",
        interval: cdk.Duration.seconds(30),
        healthyThresholdCount: 2,
      },
      deregistrationDelay: cdk.Duration.seconds(30),
    });

    this.albDnsName = alb.loadBalancerDnsName;

    new cdk.CfnOutput(this, "AlbUrl", {
      value: `http://${alb.loadBalancerDnsName}`,
      description: "ALB URL (internal — access the app via the CloudFront URL)",
    });

    new cdk.CfnOutput(this, "EcsServiceName", {
      value: service.serviceName,
      description: "ECS Fargate service name — used by cd.yml to trigger redeployments",
    });
  }
}
