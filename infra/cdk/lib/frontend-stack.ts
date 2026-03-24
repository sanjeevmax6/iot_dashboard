import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import { Construct } from "constructs";

interface FrontendStackProps extends cdk.StackProps {
  // ALB DNS name from EcsStack — CloudFront proxies /api/* here
  albDnsName: string;
}

export class FrontendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);
    const { albDnsName } = props;

    // S3 bucket (private — only CloudFront can read it via OAC)
    const bucket = new s3.Bucket(this, "FrontendBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL, // Learned that BLOCK_ALL means nobody can access it directly except for Cloudfront for spinning up and down in my case
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // ALB
    const apiOrigin = new origins.HttpOrigin(albDnsName, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
      // Standard API calls — 30s is plenty
      readTimeout: cdk.Duration.seconds(30),
    });

    // SSE streaming origin — needs the maximum CloudFront read timeout (60s)
    const sseOrigin = new origins.HttpOrigin(albDnsName, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
      readTimeout: cdk.Duration.seconds(60),
    });

    // CloudFront distribution
    const distribution = new cloudfront.Distribution(this, "Distribution", {
      // Default: serve React SPA from S3
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(bucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },

      additionalBehaviors: {
        // SSE chat endpoint — buffering disabled, max timeout (for streaming my messages as it comes for AI tool)
        // Very important
        "/api/analysis/chat/*": {
          origin: sseOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
        // All other API routes
        "/api/*": {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },

      // SPA fallback: 403/404 from S3 → serve index.html (React Router handles the route)
      defaultRootObject: "index.html",
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
        },
      ],
    });

    // Outputs (copy these values into GitHub repository variables) 
    new cdk.CfnOutput(this, "FrontendUrl", {
      value: `https://${distribution.distributionDomainName}`,
      description: "Your app URL",
    });

    new cdk.CfnOutput(this, "S3BucketName", {
      value: bucket.bucketName,
      description: "Set as S3_BUCKET GitHub variable",
    });

    new cdk.CfnOutput(this, "CloudFrontDistributionId", {
      value: distribution.distributionId,
      description: "Set as CLOUDFRONT_DISTRIBUTION_ID GitHub variable",
    });
  }
}
