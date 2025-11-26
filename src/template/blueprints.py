poja_config_blueprints = {
    "settings.gradle": """
rootProject.name = '{geo-jobs_env}'

    """,

    ".github/workflows/cd-compute-permission.yml":"""
name: CD compute permission

on:
  push:
    branches:
      - 'prod'
      - 'preprod'

  workflow_dispatch:

jobs:
  cd-event:
    if: github.ref_name == 'prod' || github.ref_name == 'preprod'

    runs-on: ubuntu-latest

    timeout-minutes: 20

    env:
      AWS_REGION: eu-west-3

    steps:
      - name: Checkout
        uses: actions/checkout@v4.1.6

      - uses: hei-school/aws-credentials-setter@v1.0.3
        with:
          secrets: ${{{{ toJSON(secrets) }}}}
          region: ${{{{ env.AWS_REGION }}}}

      - name: Deploy permission stack
        uses: aws-actions/aws-cloudformation-github-deploy@v1
        with:
          name: ${{{{ github.ref_name }}}}-permission-{geo-jobs_env}
          template: cf-stacks/compute-permission-stack.yml
          tags: "[ {{ \"Key\": \"app\", \"Value\": \"{geo-jobs_env}\" }}, {{ \"Key\": \"env\", \"Value\": \"${{{{ github.ref_name }}}}\" }}, {{ \"Key\": \"user:poja\", \"Value\": \"geo-jobs\" }} ]"
          capabilities: CAPABILITY_NAMED_IAM
          no-fail-on-empty-changeset: "1"
          parameter-overrides:
            "Env=${{{{ github.ref_name }}}}"

    """,

    ".github/workflows/cd-compute.yml":"""
name: CD compute

on:
  push:
    branches:
      - 'prod'
      - 'preprod'

  workflow_dispatch:
    inputs:
      run_tests:
        type: choice
        required: false
        default: 'yes'
        description: Run tests?
        options:
          - 'yes'
          - 'no'

  workflow_call:

jobs:
  deploy-api:
    if: ${{{{ github.ref_name == 'prod' || github.ref_name == 'preprod' }}}}
    runs-on: ubuntu-latest
    timeout-minutes: 15

    env:
      AWS_REGION: eu-west-3

    steps:
      - uses: actions/checkout@v4.1.6

      - uses: actions/setup-java@v4.2.1
        with:
          java-version: '21'
          distribution: 'corretto'

      - uses: hei-school/aws-credentials-setter@v1.0.3
        with:
          secrets: ${{{{ toJSON(secrets) }}}}
          region: ${{{{ env.AWS_REGION }}}}

      - name: Disable tests
        if: ${{{{ github.event.inputs.run_tests == 'no' }}}}
        run: |
          printf "tasks.named('test').configure {{\\n    enabled = false\\n}}" >> build.gradle

      - run: sam build

      - name: Deploy application
        run: sam deploy --no-confirm-changeset --no-fail-on-empty-changeset --stack-name ${{{{ github.ref_name }}}}-compute-{geo-jobs_env} --capabilities CAPABILITY_IAM --parameter-overrides Env=${{{{ github.ref_name }}}} --resolve-s3 --tags app={geo-jobs_env} env=${{{{ github.ref_name }}}} user:poja={geo-jobs_env}

  health-check-infra:
    needs: [deploy-api]
    if: ${{{{ needs.deploy-api.result == 'success' && (github.ref_name == 'prod' || github.ref_name == 'preprod') }}}}
    uses: ./.github/workflows/health-check-infra.yml
    secrets: inherit
    """,

    ".github/workflows/cd-event.yml": """
name: CD event

on:
  push:
    branches:
      - 'prod'
      - 'preprod'

  workflow_dispatch:

jobs:
  cd-event:
    if: github.ref_name == 'prod' || github.ref_name == 'preprod'

    runs-on: ubuntu-latest

    timeout-minutes: 20

    env:
      AWS_REGION: eu-west-3

    steps:
      - name: Checkout
        uses: actions/checkout@v4.1.6

      - uses: hei-school/aws-credentials-setter@v1.0.3
        with:
          secrets: ${{{{ toJSON(secrets) }}}}
          region: ${{{{ env.AWS_REGION }}}}

      - name: Deploy event stack
        uses: aws-actions/aws-cloudformation-github-deploy@v1
        with:
          name: ${{{{ github.ref_name }}}}-event-{geo-jobs_env}
          template: cf-stacks/event-stack.yml
          tags: "[ {{ \"Key\": \"app\", \"Value\": \"{geo-jobs_env}\" }}, {{ \"Key\": \"env\", \"Value\": \"${{{{ github.ref_name }}}}\" }}, {{ \"Key\": \"user:poja\", \"Value\": \"{geo-jobs_env}\" }} ]"
          capabilities: CAPABILITY_NAMED_IAM
          no-fail-on-empty-changeset: "1"
          parameter-overrides:
            "Env=${{{{ github.ref_name }}}}"
""",

    ".github/workflows/cd-storage-bucket.yml": """
name: CD storage bucket

on:
  push:
    branches:
      - 'prod'
      - 'preprod'

  workflow_dispatch:

jobs:
  cd-storage:
    if: github.ref_name == 'prod' || github.ref_name == 'preprod'

    runs-on: ubuntu-latest

    timeout-minutes: 20

    env:
      AWS_REGION: eu-west-3

    steps:
      - uses: actions/checkout@v4.1.6

      - uses: hei-school/aws-credentials-setter@v1.0.3
        with:
          secrets: ${{{{ toJSON(secrets) }}}}
          region: ${{{{ env.AWS_REGION }}}}

      - name: Deploy bucket stack
        uses: aws-actions/aws-cloudformation-github-deploy@v1
        with:
          name: ${{{{ github.ref_name }}}}-bucket-{geo-jobs_env}
          template: cf-stacks/storage-bucket-stack.yml
          tags: "[ {{ \"Key\": \"app\", \"Value\": \"{geo-jobs_env}\" }}, {{ \"Key\": \"env\", \"Value\": \"${{{{ github.ref_name }}}}\" }}, {{ \"Key\": \"user:poja\", \"Value\": \"{geo-jobs_env}\" }} ]"
          capabilities: CAPABILITY_NAMED_IAM
          no-fail-on-empty-changeset: "1"
          parameter-overrides:
            "Env=${{{{ github.ref_name }}}}"
""",

    ".shell/checkAsyncStack.sh": """
sudo apt-get install jq
export API_URL_SSM="`aws ssm get-parameter --name /{geo-jobs_env}/$1/api/url`"
export API_URL=`echo $API_URL_SSM | jq -r '.Parameter.Value'`
created_uuids=$(curl --fail -X GET "$API_URL$2")
sleep 90
output=$(curl -s -X POST -H "Content-Type: application/json" -d "$created_uuids" "$API_URL/health/event/uuids")
if [ "$output" = "OK" ]; then
  exit 0
else
  exit 1
fi
""",

    ".shell/checkHealth.sh": """
sudo apt-get install jq
export API_URL_SSM="`aws ssm get-parameter --name /{geo-jobs_env}/$1/api/url`"
export API_URL=`echo $API_URL_SSM | jq -r '.Parameter.Value'`
curl --fail "$API_URL$2"
""",

    "build.gradle": """
import org.apache.tools.ant.taskdefs.condition.Os
import org.openapitools.generator.gradle.plugin.tasks.GenerateTask

plugins {{
    id 'java'
    id 'org.springframework.boot' version '3.2.2'
    id 'io.spring.dependency-management' version '1.1.3'

    id 'org.openapi.generator' version '7.7.0'

    id 'jacoco'

    id "org.sonarqube" version "4.4.1.3373" 
}}

jacoco {{
    toolVersion = "0.8.11"
}}

sonarqube {{
    properties {{
        property "sonar.java.source", "21"
        property "sonar.java.target", "21"
    }}
}} 

repositories {{
mavenLocal()
maven {{
  url 'https://repo.osgeo.org/repository/geotools-releases'
}}
    mavenCentral()
}}

java {{
    group = 'app.bpartners.geojobs'
    sourceCompatibility = '21'
    targetCompatibility = '21'
}}

configurations {{
    compileOnly {{
        extendsFrom annotationProcessor
    }}
}}

task generateJavaClient(type: GenerateTask) {{
    generatorName = "java"
    inputSpec = "$rootDir/doc/api.yml".toString()
    outputDir = "$buildDir/gen".toString()
    apiPackage = "app.bpartners.geojobs.endpoint.rest.api"
    invokerPackage = "app.bpartners.geojobs.endpoint.rest.client"
    modelPackage = "app.bpartners.geojobs.endpoint.rest.model"

    configOptions = [
            serializableModel: "true",
            serializationLibrary: "jackson",
            dateLibrary: "custom"
    ]
    typeMappings = [
            // What date-time type to use when? https://i.stack.imgur.com/QPhGW.png
            Date: "java.time.LocalDate",
            DateTime: "java.time.Instant",
    ]
    library = "native"

    groupId = 'app.bpartners'
    id = '{geo-jobs_env}-gen'
    skipValidateSpec = false
    logToStderr = true
    generateAliasAsModel = false
    enablePostProcessFile = false
}}
task generateTsClient(type: org.openapitools.generator.gradle.plugin.tasks.GenerateTask) {{
    generatorName = "typescript-axios"
    inputSpec = "$rootDir/doc/api.yml".toString()
    outputDir = "$buildDir/gen-ts".toString()
    typeMappings = [
            Date    : "Date",
            DateTime: "Date",
    ]
    additionalProperties = [
            enumPropertyNaming: "original",
            npmName           : "@{geo-jobs_env}/typescript-client",
            npmVersion        : project.properties["args"] ?: "latest"
    ]
}}
task publishJavaClientToMavenLocal(type: Exec, dependsOn: generateJavaClient) {{
    if (Os.isFamily(Os.FAMILY_WINDOWS)){{
        commandLine './.shell/publish_gen_to_maven_local.bat'
    }} else {{
        commandLine './.shell/publish_gen_to_maven_local.sh'
    }}
}}
tasks.compileJava.dependsOn publishJavaClientToMavenLocal


test {{
    maxParallelForks = Runtime.runtime.availableProcessors().intdiv(2) ?: 1
    useJUnitPlatform()
    finalizedBy jacocoTestCoverageVerification
    minHeapSize = "8g"
    maxHeapSize = "10g"
}}

jacocoTestCoverageVerification {{
    dependsOn test
    afterEvaluate {{
        classDirectories.setFrom(files(classDirectories.files.collect {{
            fileTree(dir: it, exclude: [
                    "**/gen/**"
            ])
        }}))
    }}
    violationRules {{
        rule {{
            limit {{
                counter = "LINE"
                minimum = 0.7
            }}
        }}
    }}
    finalizedBy jacocoTestReport
}}

jacocoTestReport {{
    reports {{
        xml.required = true
        html.required = true
    }}
    afterEvaluate {{
        // Need to be duplicated like this from jacocoTestCoverageVerification,
        // else display coverageRate is inconsistent with what was computed during coverage...
        classDirectories.setFrom(files(classDirectories.files.collect {{
            fileTree(dir: it, exclude: [
                    "**/gen/**"
            ])
        }}))
    }}
    doLast {{
        def coverageReportFile = file("$rootDir/build/reports/jacoco/test/jacocoTestReport.xml")

        if (coverageReportFile.exists()) {{
            def xmlParser = new XmlParser()
            xmlParser.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false)
            xmlParser.setFeature("http://apache.org/xml/features/disallow-doctype-decl", false)

            def xml = xmlParser.parse(coverageReportFile)

            def lineCounter = xml.'counter'.find {{ it.@type == 'LINE' }}
            if (lineCounter != null) {{
                def totalLines = lineCounter.@missed?.toInteger() + lineCounter.@covered?.toInteger() ?: 0
                def coveredLines = lineCounter.@covered?.toInteger() ?: 0
                if (totalLines > 0) {{
                    def coverageRate = coveredLines / totalLines.toDouble() * 100
                    println "Total Line Coverage Rate: ${{coverageRate.round(2)}}%"
                }} else {{
                    println "No lines were covered or missed in the report."
                }}
            }} else {{
                println "No LINE coverage counter found in the JaCoCo report."
            }}
        }} else {{
            println "No JaCoCo coverage report found. Make sure you run 'gradle test jacocoTestReport' first."
        }}
    }}
}}

dependencies {{
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.flywaydb:flyway-core'
    testImplementation 'org.testcontainers:postgresql:1.20.0'
    implementation 'org.postgresql:postgresql'
    implementation 'org.xerial:sqlite-jdbc:3.45.1.0'
    implementation 'org.hibernate.orm:hibernate-community-dialects:6.4.3.Final'

    implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310'

    implementation 'com.amazonaws.serverless:aws-serverless-java-container-springboot3:2.1.0'
    implementation 'software.amazon.awssdk:aws-query-protocol:2.20.26'

    implementation 'com.amazonaws:aws-lambda-java-core:1.2.3'
    implementation 'com.amazonaws:aws-lambda-java-events:3.11.3'
    implementation 'software.amazon.awssdk:sqs:2.21.40'
    implementation 'software.amazon.awssdk:eventbridge:2.21.40'
    implementation 'software.amazon.awssdk:s3:2.21.40'
    implementation 'software.amazon.awssdk:s3-transfer-manager:2.21.40'
    implementation 'software.amazon.awssdk.crt:aws-crt:0.28.12'
    implementation 'software.amazon.awssdk:ses:2.21.40'
    implementation 'software.amazon.awssdk:core:2.21.40'
    implementation 'software.amazon.awssdk:ssm:2.21.40'

    implementation 'jakarta.mail:jakarta.mail-api:2.1.2'
    implementation 'jakarta.activation:jakarta.activation-api:2.1.2'
    implementation 'com.sun.mail:jakarta.mail:2.0.1'
    implementation 'com.sun.activation:jakarta.activation:2.0.1'

    implementation 'org.apache.tika:tika-core:2.9.1'
    implementation 'org.apache.poi:poi-ooxml:5.4.1'


    implementation 'org.reflections:reflections:0.10.2'

    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
    testCompileOnly 'org.projectlombok:lombok'
    testAnnotationProcessor 'org.projectlombok:lombok'

    implementation 'org.openapitools:jackson-databind-nullable:0.2.6'
    implementation 'io.swagger:swagger-annotations:1.6.12'

    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.testcontainers:junit-jupiter:1.19.1'
    testImplementation 'org.junit-pioneer:junit-pioneer:2.2.0'


    implementation 'io.sentry:sentry-logback:7.6.0'
    implementation 'io.sentry:sentry-spring-boot-starter-jakarta:7.4.0'
    implementation 'org.springframework.boot:spring-boot-starter-security'
implementation 'app.bpartners:{geo-jobs_env}-gen:latest'
implementation 'org.thymeleaf:thymeleaf:3.1.1.RELEASE'
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310:2.16.1'
implementation 'org.geotools:gt-api:31.2'
implementation 'org.geotools:gt-geojson:31.2'
implementation 'org.geotools:gt-main:31.2'
implementation 'org.geotools:gt-referencing:31.2'
implementation 'org.geotools:gt-epsg-hsql:31.2'
    implementation 'com.github.mreutegg:laszip4j:0.20'
    implementation 'org.jgrapht:jgrapht-core:1.5.2'
    implementation 'org.citygml4j:citygml4j-cityjson:3.2.6'

}}
""",

    "cf-stacks/compute-permission-stack.yml": """
AWSTemplateFormatVersion: "2010-09-09"
Description: {geo-jobs_env} - Compute permission

Parameters:
  Env:
    Type: String

Resources:
  ExecutionRole:
    Type: AWS::IAM::Role
    Properties:
RoleName: !Join [ '', [ {geo-jobs_env}-, !Ref Env, -ExecutionRole ] ]
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/AdministratorAccess'

  ExecutionRoleArnSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '',[ /{geo-jobs_env}/ , !Ref Env , /execution/role-arn ] ]
      Type: String
      Value: !GetAtt ExecutionRole.Arn

""",

    "cf-stacks/domain-name-stack.yml": """
AWSTemplateFormatVersion: 2010-09-09
Description: {geo-jobs_env} - Domain name

Parameters:
  DomainName:
    Type: String
  CertificateArn:
    Type: String
    Description: Arn of the ACM (certificate) of the domain name **Required**
  ApiTargetId:
    Type: String
  ApiStage:
    Type: String

Resources:
  CustomDomainName:
    Type: AWS::ApiGatewayV2::DomainName
    Properties:
      DomainName: !Ref DomainName
      DomainNameConfigurations:
        - CertificateArn: !Ref CertificateArn
          EndpointType: REGIONAL
          SecurityPolicy: TLS_1_2

  ApiMapping:
    Type: AWS::ApiGatewayV2::ApiMapping
    Properties:
      DomainName: !Ref CustomDomainName
      ApiId: !Ref ApiId
      Stage: !Ref ApiStage
""",

    "cf-stacks/event-stack.yml": """
AWSTemplateFormatVersion: "2010-09-09"
Description: {geo-jobs_env} - Event

Parameters:
  Env:
    Type: String

Resources:
  MailboxQueue1:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Join ['' , [!Ref Env , -1-{geo-jobs_env}]]
      VisibilityTimeout: 901 #note(sqs-visibility): WorkerFunction1.Timeout + 1
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DeadLetterQueue1.Arn
        maxReceiveCount: 5
      SqsManagedSseEnabled: false

  MailboxQueue2:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Join [ '' , [ !Ref Env , -2-{geo-jobs_env} ] ]
      VisibilityTimeout: 901 #note(sqs-visibility): WorkerFunction2.Timeout + 1
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DeadLetterQueue2.Arn
        maxReceiveCount: 9
      SqsManagedSseEnabled: false

  MailboxQueue3:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Join [ '' , [ !Ref Env , -3-{geo-jobs_env} ] ]
      VisibilityTimeout: 901 #note(sqs-visibility): WorkerFunction2.Timeout + 1
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DeadLetterQueue3.Arn
        maxReceiveCount: 9
      SqsManagedSseEnabled: false

  MailboxQueue4:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Join [ '' , [ !Ref Env , -4-{geo-jobs_env} ] ]
      VisibilityTimeout: 901 #note(sqs-visibility): WorkerFunction2.Timeout + 1
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DeadLetterQueue4.Arn
        maxReceiveCount: 9
      SqsManagedSseEnabled: false

  DeadLetterQueue1:
    Type: AWS::SQS::Queue
    Properties:
      QueueName:  !Join ['' , [!Ref Env , -1-{geo-jobs_env}-dl]]
      SqsManagedSseEnabled: false

  DeadLetterQueue2:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Join [ '' , [ !Ref Env , -2-{geo-jobs_env}-dl ] ]
      SqsManagedSseEnabled: false

  DeadLetterQueue3:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Join [ '' , [ !Ref Env , -3-{geo-jobs_env}-dl ] ]
      SqsManagedSseEnabled: false

  DeadLetterQueue4:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Join [ '' , [ !Ref Env , -4-{geo-jobs_env}-dl ] ]
      SqsManagedSseEnabled: false

  MailboxQueuePolicy:
    Type: AWS::SQS::QueuePolicy
    Properties:
      Queues:
        - !Ref MailboxQueue1
        - !Ref MailboxQueue2
        - !Ref MailboxQueue3
        - !Ref MailboxQueue4
      PolicyDocument:
        Version: "2008-10-17"
        Id: "MailboxQueue_Policy"
        Statement:
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue1.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue2.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue3.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue4.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root
          - Action:
              - "SQS:SendMessage"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue1.Arn
            Principal:
              Service:
                - "events.amazonaws.com"
            Condition:
              ArnEquals:
                AWS:SourceArn: !GetAtt EventBridgeRule1.Arn
          - Action:
              - "SQS:SendMessage"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue2.Arn
            Principal:
              Service:
                - "events.amazonaws.com"
            Condition:
              ArnEquals:
                AWS:SourceArn: !GetAtt EventBridgeRule2.Arn
          - Action:
              - "SQS:SendMessage"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue3.Arn
            Principal:
              Service:
                - "events.amazonaws.com"
            Condition:
              ArnEquals:
                AWS:SourceArn: !GetAtt EventBridgeRule3.Arn
          - Action:
              - "SQS:SendMessage"
            Effect: "Allow"
            Resource: !GetAtt MailboxQueue4.Arn
            Principal:
              Service:
                - "events.amazonaws.com"
            Condition:
              ArnEquals:
                AWS:SourceArn: !GetAtt EventBridgeRule4.Arn

  DeadLetterQueuePolicy:
    Type: AWS::SQS::QueuePolicy
    Properties:
      Queues:
        - !Ref DeadLetterQueue1
        - !Ref DeadLetterQueue2
        - !Ref DeadLetterQueue3
        - !Ref DeadLetterQueue4
      PolicyDocument:
        Version: "2008-10-17"
        Id: "DeadLetterQueue_Policy"
        Statement:
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt DeadLetterQueue1.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt DeadLetterQueue2.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt DeadLetterQueue3.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root
          - Action:
              - "SQS:*"
            Effect: "Allow"
            Resource: !GetAtt DeadLetterQueue4.Arn
            Principal:
              AWS:
                - !Sub arn:aws:iam::${{AWS::AccountId}}:root

  MailboxQueue1SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join ['' , [/{geo-jobs_env}/ , !Ref Env , /1/sqs/mailbox-queue-url]]
      Type: String
      Value: !Ref MailboxQueue1

  MailboxQueue1SSMArn:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join ['' , [/{geo-jobs_env}/ , !Ref Env , /1/sqs/mailbox-queue-arn]]
      Type: String
      Value: !GetAtt MailboxQueue1.Arn

  MailboxQueue2SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /2/sqs/mailbox-queue-url ] ]
      Type: String
      Value: !Ref MailboxQueue2

  MailboxQueue2SSMArn:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /2/sqs/mailbox-queue-arn ] ]
      Type: String
      Value: !GetAtt MailboxQueue2.Arn

  MailboxQueue3SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /3/sqs/mailbox-queue-url ] ]
      Type: String
      Value: !Ref MailboxQueue3

  MailboxQueue3SSMArn:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /3/sqs/mailbox-queue-arn ] ]
      Type: String
      Value: !GetAtt MailboxQueue3.Arn

  MailboxQueue4SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /4/sqs/mailbox-queue-url ] ]
      Type: String
      Value: !Ref MailboxQueue4

  MailboxQueue4SSMArn:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /4/sqs/mailbox-queue-arn ] ]
      Type: String
      Value: !GetAtt MailboxQueue4.Arn

  DeadLetterQueue1SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join ['' , [/{geo-jobs_env}/ , !Ref Env , /1/sqs/dead-letter-queue-url]]
      Type: String
      Value: !Ref DeadLetterQueue1

  DeadLetterQueue1ArnSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /1/sqs/dead-letter-queue-arn ] ]
      Type: String
      Value: !GetAtt DeadLetterQueue1.Arn

  DeadLetterQueue2SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /2/sqs/dead-letter-queue-url ] ]
      Type: String
      Value: !Ref DeadLetterQueue1

  DeadLetterQueue2ArnSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /2/sqs/dead-letter-queue-arn ] ]
      Type: String
      Value: !GetAtt DeadLetterQueue1.Arn

  DeadLetterQueue3SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /3/sqs/dead-letter-queue-url ] ]
      Type: String
      Value: !Ref DeadLetterQueue1

  DeadLetterQueue3ArnSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /3/sqs/dead-letter-queue-arn ] ]
      Type: String
      Value: !GetAtt DeadLetterQueue1.Arn

  DeadLetterQueue4SSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /4/sqs/dead-letter-queue-url ] ]
      Type: String
      Value: !Ref DeadLetterQueue1

  DeadLetterQueue4ArnSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '' , [ /{geo-jobs_env}/ , !Ref Env , /4/sqs/dead-letter-queue-arn ] ]
      Type: String
      Value: !GetAtt DeadLetterQueue1.Arn

  EventBridgeBus:
    Type: AWS::Events::EventBus
    Properties:
      Name: !Join ['', [!Ref Env, -{geo-jobs_env}]]

  EventBridgeArchive:
    Type: AWS::Events::Archive
    Properties:
      ArchiveName: !Join ['', [!Ref Env, -{geo-jobs_env}, -archive]]
      SourceArn: !GetAtt EventBridgeBus.Arn

  EventBridgeRule1:
    Type: AWS::Events::Rule
    Properties:
      Name: !Join ['', [!Ref Env, -1-{geo-jobs_env}, -from-api-to-api]]
      EventBusName: !GetAtt EventBridgeBus.Name
      EventPattern:
        source:
          - app.bpartners.geojobs.event1
      Targets:
        - Arn: !GetAtt MailboxQueue1.Arn
          Id: !Join ['', [!Ref Env, -1-{geo-jobs_env}, -api-mailbox]]

  EventBridgeRule2:
    Type: AWS::Events::Rule
    Properties:
      Name: !Join [ '', [ !Ref Env, -2-{geo-jobs_env}, -from-api-to-api ] ]
      EventBusName: !GetAtt EventBridgeBus.Name
      EventPattern:
        source:
          - app.bpartners.geojobs.event2
      Targets:
        - Arn: !GetAtt MailboxQueue2.Arn
          Id: !Join [ '', [ !Ref Env, -2-{geo-jobs_env}, -api-mailbox ] ]

  EventBridgeRule3:
    Type: AWS::Events::Rule
    Properties:
      Name: !Join [ '', [ !Ref Env, -3-{geo-jobs_env}, -from-api-to-api ] ]
      EventBusName: !GetAtt EventBridgeBus.Name
      EventPattern:
        source:
          - app.bpartners.geojobs.event3
      Targets:
        - Arn: !GetAtt MailboxQueue3.Arn
          Id: !Join [ '', [ !Ref Env, -3-{geo-jobs_env}, -api-mailbox ] ]

  EventBridgeRule4:
    Type: AWS::Events::Rule
    Properties:
      Name: !Join [ '', [ !Ref Env, -4-{geo-jobs_env}, -from-api-to-api ] ]
      EventBusName: !GetAtt EventBridgeBus.Name
      EventPattern:
        source:
          - app.bpartners.geojobs.event4
      Targets:
        - Arn: !GetAtt MailboxQueue4.Arn
          Id: !Join [ '', [ !Ref Env, -4-{geo-jobs_env}, -api-mailbox ] ]

  EventBridgeBusNameSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join ['',[/{geo-jobs_env}/ , !Ref Env , /eventbridge/bus-name]]
      Type: String
      Value: !GetAtt EventBridgeBus.Name

  EventBridgeBusArnSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '',[ /{geo-jobs_env}/ , !Ref Env , /eventbridge/bus-arn ] ]
      Type: String
      Value: !GetAtt EventBridgeBus.Arn

Outputs:
  MailboxQueue1URL:
    Value: !Ref MailboxQueue1SSM
  MailboxQueue1Arn:
    Value: !Ref MailboxQueue1SSMArn
  DeadLetterQueue1URL:
    Value: !Ref DeadLetterQueue1SSM
  DeadLetterQueue1Arn:
    Value: !Ref DeadLetterQueue1ArnSSM
  MailboxQueue2URL:
    Value: !Ref MailboxQueue2SSM
  MailboxQueue2Arn:
    Value: !Ref MailboxQueue2SSMArn
  DeadLetterQueue2URL:
    Value: !Ref DeadLetterQueue2SSM
  DeadLetterQueue2Arn:
    Value: !Ref DeadLetterQueue2ArnSSM
  MailboxQueue3URL:
    Value: !Ref MailboxQueue3SSM
  MailboxQueue3Arn:
    Value: !Ref MailboxQueue3SSMArn
  DeadLetterQueue3URL:
    Value: !Ref DeadLetterQueue3SSM
  DeadLetterQueue3Arn:
    Value: !Ref DeadLetterQueue3ArnSSM
  MailboxQueue4URL:
    Value: !Ref MailboxQueue4SSM
  MailboxQueue4Arn:
    Value: !Ref MailboxQueue4SSMArn
  DeadLetterQueue4URL:
    Value: !Ref DeadLetterQueue4SSM
  DeadLetterQueue4Arn:
    Value: !Ref DeadLetterQueue4ArnSSM
  EventBridgeBusName:
    Value: !Ref EventBridgeBusNameSSM
  EventBridgeArnName:
    Value: !Ref EventBridgeBusArnSSM

""",

    "cf-stacks/storage-bucket-stack.yml": """
AWSTemplateFormatVersion: 2010-09-09
Description: CD storage database

Parameters:
  Env:
    Type: String

Resources:
  Bucket:
    Type: AWS::S3::Bucket
    DeletionPolicy: Retain
    Properties:
      VersioningConfiguration:
        Status: Enabled
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  BucketSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join ['', [/{geo-jobs_env}/, !Ref Env, /s3/bucket-name]]
      Type: String
      Value: !Ref Bucket

Outputs:
  BucketSSM:
    Value: !Ref BucketSSM
""",

    "poja-custom-java-deps.txt": """
implementation 'org.springframework.boot:spring-boot-starter-security'
implementation 'app.bpartners:{geo-jobs_env}-gen:latest'
implementation 'org.thymeleaf:thymeleaf:3.1.1.RELEASE'
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310:2.16.1'
implementation 'org.geotools:gt-api:31.2'
implementation 'org.geotools:gt-geojson:31.2'
implementation 'org.geotools:gt-main:31.2'
implementation 'org.geotools:gt-referencing:31.2'
implementation 'org.geotools:gt-epsg-hsql:31.2'
implementation 'com.github.mreutegg:laszip4j:0.20'
implementation 'org.jgrapht:jgrapht-core:1.5.2'
implementation 'org.citygml4j:citygml4j-cityjson:3.2.6'
   
""",

    "poja-custom-java-env-vars.txt": """
TILES_DOWNLOADER_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/tiles/downloader/url}}}}'
ADMIN_API_KEY: !Sub '{{{{resolve:ssm:/bpartners-geo-jobs/${{Env}}/admin/api-key}}}}'
ANNOTATOR_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/annotator/url}}}}'
ANNOTATOR_API_KEY: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/annotator/api/key}}}}'
ANNOTATOR_GEOJOBS_USER_INFO: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/annotator/user/info}}}}'
TILES_DOWNLOADER_MOCK_ACTIVATED: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/tiles-downloader-activated}}}}'
OBJECTS_DETECTOR_MOCK_ACTIVATED: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/objects-detector-activated}}}}'
SPRING_DATASOURCE_URL: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/db/url}}}}'
SPRING_DATASOURCE_USERNAME: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/db/username}}}}'
SPRING_DATASOURCE_PASSWORD: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/db/password}}}}'
README_MONITOR_IS_DEVELOPMENT: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/monitor/is-development}}}}'
README_MONITOR_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/monitor/url}}}}'
README_MONITOR_API_KEY: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/monitor/apikey}}}}'
ADMIN_EMAIL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/admin/email}}}}'
README_WEBHOOK_SECRET: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/webhook/secret}}}}'
BPARTNERS_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/bpartners/api/url}}}}'
GEOSERVER_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/geoserver/api/url}}}}'
IGN_LIDAR_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/ign/lidar/api/url}}}}'
ROOF_COVERING_DETECTION_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/covering/detection/api/url}}}}'
""",

    "poja.yml": """
compute:
  api_gateway_timeout: null
  frontal_function_invocation_method: lambda-url
  frontal_function_timeout: 300
  frontal_memory: 2048
  with_queues_nb: 3
  worker_1_batch: 5
  worker_1_memory: 1024
  worker_2_batch: 5
  worker_2_memory: 1024
  worker_3_memory: 1024
  worker_4_memory: 10240
  worker_function_1_timeout: 900
  worker_function_2_timeout: 900
  worker_function_3_timeout: 900
  worker_function_4_timeout: 900
concurrency:
  frontal_reserved_concurrent_executions_nb: null
  worker_1_reserved_concurrent_executions_nb: 2
  worker_2_reserved_concurrent_executions_nb: 2
  worker_3_reserved_concurrent_executions_nb: 2
  worker_4_reserved_concurrent_executions_nb: 2
database:
  with_database: None
emailing:
  ses_source: lou@bpartners.app
gen_api_client:
  aws_account_id: 'null'
  codeartifact_domain_name: 'null'
  codeartifact_repository_name: 'null'
  ts_client_api_url_env_var_name: ''
  ts_client_default_openapi_server_url: ''
  with_gen_clients: 'true'
  with_publish_to_npm_registry: 'false'
general:
  app_name: geo-jobs
  cli_version: 20.0.6
  custom_java_deps: poja-custom-java-deps.txt
  custom_java_env_vars: poja-custom-java-env-vars.txt
  custom_java_repositories: poja-custom-java-repositories.txt
  package_full_name: app.bpartners.geojobs
  poja_domain_owner: 088312068315
  poja_python_repository_domain: python-numer-tech
  poja_python_repository_name: numer-python-store
  with_snapstart: 'true'
integration:
  with_codeql: 'true'
  with_file_storage: 'true'
  with_sentry: 'true'
  with_sonar: 'true'
  with_swagger_ui: 'false'
networking:
  region: eu-west-3
  ssm_sg_id: /bpartners-imagery/sg/id
  ssm_subnet1_id: /bpartners-imagery/private/subnet1/id
  ssm_subnet2_id: /bpartners-imagery/private/subnet2/id
  with_own_vpc: 'true'
scheduled_tasks: null
testing:
  jacoco_min_coverage: '0.8'
  java_facade_it: FacadeIT

""",

    "template.yml": """
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: {geo-jobs_env} - Computation and API

Globals:
  Function:
    CodeUri: .
    Runtime: java21
    Tracing: Active
    Architectures:
      - arm64
    EventInvokeConfig:
      MaximumRetryAttempts: 0
    AutoPublishAlias: live
    SnapStart:
      ApplyOn: PublishedVersions
    VpcConfig:
      SecurityGroupIds:
        - !Sub '{{{{resolve:ssm:/bpartners-imagery/sg/id}}}}'
      SubnetIds:
        - !Sub '{{{{resolve:ssm:/bpartners-imagery/private/subnet1/id}}}}'
        - !Sub '{{{{resolve:ssm:/bpartners-imagery/private/subnet2/id}}}}'
    Environment:
      Variables:
        ENV: !Ref Env
        AWS_S3_BUCKET: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/s3/bucket-name}}}}'
        AWS_SES_SOURCE: lou@bpartners.app
        AWS_EVENTBRIDGE_BUS: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/eventbridge/bus-name}}}}'
        AWS_EVENT_STACK_1_SQS_QUEUE_URL: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/1/sqs/mailbox-queue-url}}}}'
        AWS_EVENT_STACK_2_SQS_QUEUE_URL: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/2/sqs/mailbox-queue-url}}}}'
        AWS_EVENT_STACK_3_SQS_QUEUE_URL: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/3/sqs/mailbox-queue-url}}}}'
        AWS_EVENT_STACK_4_SQS_QUEUE_URL: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/4/sqs/mailbox-queue-url}}}}'
        
        SENTRY_DSN: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/sentry/dsn}}}}'
        SENTRY_ENVIRONMENT: !Ref Env
        TILES_DOWNLOADER_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/tiles/downloader/url}}}}'
        TILE_DETECTION_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/tiles/detection/url}}}}'
        ADMIN_API_KEY: !Sub '{{{{resolve:ssm:/bpartners-geo-jobs/${{Env}}/admin/api-key}}}}'
        ANNOTATOR_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/annotator/url}}}}'
        ANNOTATOR_API_KEY: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/annotator/api/key}}}}'
        ANNOTATOR_GEOJOBS_USER_INFO: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/annotator/user/info}}}}'
        TILES_DOWNLOADER_MOCK_ACTIVATED: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/tiles-downloader-activated}}}}'
        OBJECTS_DETECTOR_MOCK_ACTIVATED: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/objects-detector-activated}}}}'
        SPRING_DATASOURCE_URL: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/db/url}}}}'
        SPRING_DATASOURCE_USERNAME: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/db/username}}}}'
        SPRING_DATASOURCE_PASSWORD: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/db/password}}}}'
        README_MONITOR_IS_DEVELOPMENT: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/monitor/is-development}}}}'
        README_MONITOR_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/monitor/url}}}}'
        README_MONITOR_API_KEY: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/monitor/apikey}}}}'
        ADMIN_EMAIL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/admin/email}}}}'
        README_WEBHOOK_SECRET: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/readme/webhook/secret}}}}'
        BPARTNERS_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/bpartners/api/url}}}}'
        GEOSERVER_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/geoserver/api/url}}}}'
        IGN_LIDAR_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/ign/lidar/api/url}}}}'
        ROOF_COVERING_DETECTION_API_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/covering/detection/api/url}}}}'
        GOOGLE_CAPTCHA_SECRET: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/google/captcha/secret}}}}'
        GOOGLE_CAPTCHA_URL: !Sub '{{{{resolve:ssm:/geo-jobs/${{Env}}/google/captcha/url}}}}'


Parameters:
  Env:
    Type: String

Resources:
  
  FrontalFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.bpartners.geojobs.handler.LambdaHandler::handleRequest
      MemorySize: 2048
      Timeout: 300
      Role: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/execution/role-arn}}}}'
      
      FunctionUrlConfig:
        AuthType: NONE
        InvokeMode: BUFFERED
        

  WorkerFunction1:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.bpartners.geojobs.handler.MailboxEventHandler::handleRequest
      MemorySize: 1024
      Timeout: 900 #note(sqs-visibility)
      Role: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/execution/role-arn}}}}'
      Events:
        AllEvents:
          Type: SQS
          Properties:
            Queue: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/1/sqs/mailbox-queue-arn}}}}'
            BatchSize: 1
      ReservedConcurrentExecutions: 100

  WorkerFunction2:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.bpartners.geojobs.handler.MailboxEventHandler::handleRequest
      MemorySize: 2048
      Timeout: 900 #note(sqs-visibility)
      Role: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/execution/role-arn}}}}'
      Events:
        AllEvents:
          Type: SQS
          Properties:
            Queue: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/2/sqs/mailbox-queue-arn}}}}'
            BatchSize: 1
      ReservedConcurrentExecutions: 100

  WorkerFunction3:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.bpartners.geojobs.handler.MailboxEventHandler::handleRequest
      MemorySize: 1024
      Timeout: 900 #note(sqs-visibility)
      Role: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/execution/role-arn}}}}'
      Events:
        AllEvents:
          Type: SQS
          Properties:
            Queue: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/3/sqs/mailbox-queue-arn}}}}'
            BatchSize: 1
      ReservedConcurrentExecutions: 10

  WorkerFunction4:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.bpartners.geojobs.handler.MailboxEventHandler::handleRequest
      MemorySize: 7077
      Timeout: 900 #note(sqs-visibility)
      Role: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/execution/role-arn}}}}'
      SnapStart:
        ApplyOn: None
      EphemeralStorage:
        Size: 1024
      Events:
        AllEvents:
          Type: SQS
          Properties:
            Queue: !Sub '{{{{resolve:ssm:/{geo-jobs_env}/${{Env}}/4/sqs/mailbox-queue-arn}}}}'
            BatchSize: 1
      ReservedConcurrentExecutions: 10

  ApiUrlSSM:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Join [ '', [ /{geo-jobs_env}/, !Ref Env, /api/url ] ]
      Type: String
      Value: !GetAtt FrontalFunctionUrl.FunctionUrl
  
Outputs:
  ApiUrl:
    Description: Url to access the frontal function
    Value: !GetAtt FrontalFunctionUrl.FunctionUrl
        

""",
}
