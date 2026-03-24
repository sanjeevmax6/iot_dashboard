import * as cdk from "aws-cdk-lib";
import * as ecr from "aws-cdk-lib/aws-ecr";
import { Construct } from "constructs";

export class EcrStack extends cdk.Stack {
  public readonly repository: ecr.Repository;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.repository = new ecr.Repository(this, "BackendRepo", {
      repositoryName: "iot-dashboard-backend",
      removalPolicy: cdk.RemovalPolicy.DESTROY, // added this manually for cleaner setup for this project. In a real world use case, would need to retain for backup (for rollbacks and availability)
      emptyOnDelete: true,
      imageScanOnPush: true, // AWS scans for any vulnerabilities (My reasoning: prompt injection traces can be captured)
      lifecycleRules: [
        {
          maxImageCount: 10,
          description: "Keep only the last 10 images",
        },
      ],
    });

    new cdk.CfnOutput(this, "RepositoryUri", {
      value: this.repository.repositoryUri,
      description: 'ECR repository URI — set ECR_REPOSITORY GitHub variable to "iot-dashboard-backend"',
    });
  }
}
