#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { VpcStack } from "./lib/vpc-stack";
import { EcrStack } from "./lib/ecr-stack";
import { EcsStack } from "./lib/ecs-stack";
import { FrontendStack } from "./lib/frontend-stack";

const app = new cdk.App();

// Resolve account + region from environment (set by GitHub Actions secrets)
const env: cdk.Environment = {
  account: process.env.AWS_ACCOUNT_ID ?? process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.AWS_REGION ?? process.env.CDK_DEFAULT_REGION ?? "us-east-1",
};

const vpcStack = new VpcStack(app, "IotDashboardVpc", { env });

const ecrStack = new EcrStack(app, "IotDashboardEcr", { env });

const ecsStack = new EcsStack(app, "IotDashboardEcs", {
  vpc: vpcStack.vpc,
  repository: ecrStack.repository,
  env,
});

// FrontendStack receives the ALB DNS name so CloudFront can proxy /api/* to it
new FrontendStack(app, "IotDashboardFrontend", {
  albDnsName: ecsStack.albDnsName,
  env,
});
