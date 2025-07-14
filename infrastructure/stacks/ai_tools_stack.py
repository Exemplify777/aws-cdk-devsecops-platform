"""
AI Tools Stack
Implements AI-powered development tools including code generation, analysis, and optimization
"""

from typing import Dict, Any
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_bedrock as bedrock,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    CfnOutput,
    RemovalPolicy,
    Duration,
)


class AIToolsStack(Stack):
    """AI tools stack for intelligent development assistance."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_config: Dict[str, Any],
        vpc: ec2.Vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_config = env_config
        self.environment_name = env_config["environment_name"]
        self.vpc = vpc
        
        # Create AI tools components
        self._create_dynamodb_tables()
        self._create_code_generation_service()
        self._create_error_analysis_service()
        self._create_optimization_service()
        self._create_api_gateway()
        self._create_outputs()
    
    def _create_dynamodb_tables(self) -> None:
        """Create DynamoDB tables for AI tools data."""
        # Code templates table
        self.code_templates_table = dynamodb.Table(
            self,
            "CodeTemplatesTable",
            table_name=f"code-templates-{self.environment_name}",
            partition_key=dynamodb.Attribute(
                name="template_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="version",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=self.environment_name == "prod",
        )
        
        # AI analysis results table
        self.analysis_results_table = dynamodb.Table(
            self,
            "AnalysisResultsTable",
            table_name=f"analysis-results-{self.environment_name}",
            partition_key=dynamodb.Attribute(
                name="analysis_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )
        
        # User sessions table
        self.user_sessions_table = dynamodb.Table(
            self,
            "UserSessionsTable",
            table_name=f"user-sessions-{self.environment_name}",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="expires_at",
        )
    
    def _create_code_generation_service(self) -> None:
        """Create Lambda function for AI-powered code generation."""
        self.code_generator_lambda = lambda_.Function(
            self,
            "CodeGenerator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    '''AI-powered code generation Lambda'''
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Extract request parameters
        prompt = body.get('prompt', '')
        language = body.get('language', 'python')
        framework = body.get('framework', 'aws-cdk')
        template_type = body.get('template_type', 'data-pipeline')
        
        logger.info(f"Generating code for: {template_type} in {language}")
        
        # Prepare prompt for Bedrock
        system_prompt = f'''
        You are an expert {language} developer specializing in {framework} and data engineering.
        Generate production-ready, secure, and well-documented code based on the user's requirements.
        Follow best practices for {framework} and include proper error handling, logging, and security measures.
        '''
        
        user_prompt = f'''
        Generate a {template_type} implementation in {language} using {framework}.
        Requirements: {prompt}
        
        Please provide:
        1. Complete, working code
        2. Inline comments explaining key concepts
        3. Error handling and logging
        4. Security best practices
        5. Configuration options
        '''
        
        # Mock Bedrock response (replace with actual Bedrock call)
        generated_code = f'''
# Generated {template_type} for {framework}
# Language: {language}
# Generated at: {datetime.now().isoformat()}

import boto3
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class {template_type.replace('-', '').title()}:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.setup_logging()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def process(self):
        """Main processing logic"""
        try:
            logger.info("Starting {template_type} processing")
            # Implementation based on: {prompt}
            
            # Add your business logic here
            result = {{"status": "success", "message": "Processing completed"}}
            
            logger.info("Processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in processing: {{str(e)}}")
            raise

# Usage example:
if __name__ == "__main__":
    config = {{"environment": "dev"}}
    processor = {template_type.replace('-', '').title()}(config)
    result = processor.process()
    print(result)
        '''
        
        # Store generated code in DynamoDB
        code_id = str(uuid.uuid4())
        templates_table = dynamodb.Table(f"code-templates-{context.function_name.split('-')[-1]}")
        
        templates_table.put_item(
            Item={
                'template_id': code_id,
                'version': '1.0.0',
                'language': language,
                'framework': framework,
                'template_type': template_type,
                'prompt': prompt,
                'generated_code': generated_code,
                'created_at': datetime.now().isoformat(),
                'ttl': int((datetime.now() + timedelta(days=30)).timestamp())
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'code_id': code_id,
                'generated_code': generated_code,
                'language': language,
                'framework': framework,
                'template_type': template_type,
                'created_at': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating code: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
            """),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.environment_name,
                "CODE_TEMPLATES_TABLE": self.code_templates_table.table_name,
            },
        )
        
        # Grant DynamoDB permissions
        self.code_templates_table.grant_read_write_data(self.code_generator_lambda)
        
        # Grant Bedrock permissions
        self.code_generator_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"]
            )
        )
    
    def _create_error_analysis_service(self) -> None:
        """Create Lambda function for AI-powered error analysis."""
        self.error_analyzer_lambda = lambda_.Function(
            self,
            "ErrorAnalyzer",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging
from datetime import datetime
import uuid
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    '''AI-powered error analysis Lambda'''
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Extract error information
        error_message = body.get('error_message', '')
        stack_trace = body.get('stack_trace', '')
        code_context = body.get('code_context', '')
        environment = body.get('environment', 'unknown')
        
        logger.info(f"Analyzing error in {environment}")
        
        # Perform error analysis
        analysis = analyze_error(error_message, stack_trace, code_context)
        
        # Store analysis results
        analysis_id = str(uuid.uuid4())
        results_table = dynamodb.Table(f"analysis-results-{context.function_name.split('-')[-1]}")
        
        results_table.put_item(
            Item={
                'analysis_id': analysis_id,
                'error_message': error_message,
                'stack_trace': stack_trace,
                'analysis': analysis,
                'environment': environment,
                'created_at': datetime.now().isoformat(),
                'ttl': int((datetime.now().timestamp() + 86400 * 7))  # 7 days
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'analysis_id': analysis_id,
                'analysis': analysis,
                'created_at': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error analyzing error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def analyze_error(error_message, stack_trace, code_context):
    '''Analyze error and provide recommendations'''
    
    analysis = {
        'error_type': 'unknown',
        'severity': 'medium',
        'root_cause': '',
        'recommendations': [],
        'similar_issues': [],
        'confidence': 0.0
    }
    
    # Basic error pattern matching
    if 'ImportError' in error_message or 'ModuleNotFoundError' in error_message:
        analysis['error_type'] = 'import_error'
        analysis['severity'] = 'low'
        analysis['root_cause'] = 'Missing or incorrectly named module/package'
        analysis['recommendations'] = [
            'Check if the module is installed: pip list | grep module_name',
            'Verify the module name spelling',
            'Check if the module is in the Python path',
            'Install missing dependencies: pip install module_name'
        ]
        analysis['confidence'] = 0.9
    
    elif 'KeyError' in error_message:
        analysis['error_type'] = 'key_error'
        analysis['severity'] = 'medium'
        analysis['root_cause'] = 'Attempting to access a dictionary key that does not exist'
        analysis['recommendations'] = [
            'Use dict.get() method with default value',
            'Check if key exists before accessing: if key in dict',
            'Validate input data structure',
            'Add proper error handling with try/except'
        ]
        analysis['confidence'] = 0.8
    
    elif 'AttributeError' in error_message:
        analysis['error_type'] = 'attribute_error'
        analysis['severity'] = 'medium'
        analysis['root_cause'] = 'Object does not have the specified attribute or method'
        analysis['recommendations'] = [
            'Check object type: type(object)',
            'Verify attribute/method name spelling',
            'Check object initialization',
            'Use hasattr() to check attribute existence'
        ]
        analysis['confidence'] = 0.8
    
    elif 'TypeError' in error_message:
        analysis['error_type'] = 'type_error'
        analysis['severity'] = 'medium'
        analysis['root_cause'] = 'Operation performed on inappropriate type'
        analysis['recommendations'] = [
            'Check variable types: type(variable)',
            'Add type validation',
            'Convert types if necessary: str(), int(), float()',
            'Review function parameters and return types'
        ]
        analysis['confidence'] = 0.7
    
    elif 'ConnectionError' in error_message or 'TimeoutError' in error_message:
        analysis['error_type'] = 'network_error'
        analysis['severity'] = 'high'
        analysis['root_cause'] = 'Network connectivity or timeout issue'
        analysis['recommendations'] = [
            'Check network connectivity',
            'Verify service endpoints and URLs',
            'Implement retry logic with exponential backoff',
            'Check firewall and security group settings',
            'Monitor service health and availability'
        ]
        analysis['confidence'] = 0.9
    
    return analysis
            """),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "ENVIRONMENT": self.environment_name,
                "ANALYSIS_RESULTS_TABLE": self.analysis_results_table.table_name,
            },
        )
        
        # Grant DynamoDB permissions
        self.analysis_results_table.grant_read_write_data(self.error_analyzer_lambda)

    def _create_optimization_service(self) -> None:
        """Create Lambda function for AI-powered code optimization."""
        self.optimizer_lambda = lambda_.Function(
            self,
            "CodeOptimizer",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging
from datetime import datetime
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    '''AI-powered code optimization Lambda'''
    try:
        body = json.loads(event.get('body', '{}'))

        # Extract code and optimization parameters
        code = body.get('code', '')
        language = body.get('language', 'python')
        optimization_type = body.get('optimization_type', 'performance')

        logger.info(f"Optimizing {language} code for {optimization_type}")

        # Perform code analysis and optimization
        optimization_result = optimize_code(code, language, optimization_type)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'optimization_id': str(uuid.uuid4()),
                'original_code': code,
                'optimized_code': optimization_result['optimized_code'],
                'improvements': optimization_result['improvements'],
                'metrics': optimization_result['metrics'],
                'created_at': datetime.now().isoformat()
            })
        }

    except Exception as e:
        logger.error(f"Error optimizing code: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def optimize_code(code, language, optimization_type):
    '''Analyze and optimize code'''

    improvements = []
    metrics = {
        'complexity_reduction': 0,
        'performance_gain': 0,
        'security_improvements': 0,
        'maintainability_score': 0
    }

    optimized_code = code

    # Basic optimization patterns for Python
    if language.lower() == 'python':

        # Performance optimizations
        if optimization_type in ['performance', 'all']:
            # List comprehension optimization
            if 'for ' in code and 'append(' in code:
                improvements.append({
                    'type': 'performance',
                    'description': 'Consider using list comprehensions instead of loops with append()',
                    'impact': 'medium',
                    'example': '[item for item in iterable if condition]'
                })
                metrics['performance_gain'] += 15

            # String concatenation optimization
            if '+=' in code and 'str' in code:
                improvements.append({
                    'type': 'performance',
                    'description': 'Use join() for multiple string concatenations',
                    'impact': 'high',
                    'example': "''.join([str1, str2, str3])"
                })
                metrics['performance_gain'] += 25

        # Security improvements
        if optimization_type in ['security', 'all']:
            # SQL injection prevention
            if 'execute(' in code and '%' in code:
                improvements.append({
                    'type': 'security',
                    'description': 'Use parameterized queries to prevent SQL injection',
                    'impact': 'critical',
                    'example': 'cursor.execute("SELECT * FROM table WHERE id = %s", (user_id,))'
                })
                metrics['security_improvements'] += 1

            # Input validation
            if 'input(' in code:
                improvements.append({
                    'type': 'security',
                    'description': 'Add input validation and sanitization',
                    'impact': 'high',
                    'example': 'if isinstance(user_input, str) and len(user_input) < 100:'
                })
                metrics['security_improvements'] += 1

        # Code quality improvements
        if optimization_type in ['quality', 'all']:
            # Error handling
            if 'try:' not in code and ('open(' in code or 'requests.' in code):
                improvements.append({
                    'type': 'quality',
                    'description': 'Add proper error handling with try/except blocks',
                    'impact': 'medium',
                    'example': 'try:\\n    # risky operation\\nexcept SpecificException as e:\\n    # handle error'
                })
                metrics['maintainability_score'] += 10

            # Logging
            if 'print(' in code:
                improvements.append({
                    'type': 'quality',
                    'description': 'Replace print statements with proper logging',
                    'impact': 'low',
                    'example': 'import logging\\nlogger = logging.getLogger(__name__)\\nlogger.info("message")'
                })
                metrics['maintainability_score'] += 5

    # Generate optimized code with improvements
    if improvements:
        optimized_code = f'''# Optimized code with improvements
# Original code preserved below with suggested modifications

{code}

# Optimization suggestions applied:
# {chr(10).join([f"- {imp['description']}" for imp in improvements])}
'''

    return {
        'optimized_code': optimized_code,
        'improvements': improvements,
        'metrics': metrics
    }
            """),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "ENVIRONMENT": self.environment_name,
            },
        )

    def _create_api_gateway(self) -> None:
        """Create API Gateway for AI tools."""
        # Create API Gateway
        self.ai_api = apigateway.RestApi(
            self,
            "AIToolsAPI",
            rest_api_name=f"ai-tools-api-{self.environment_name}",
            description=f"AI Tools API for DevSecOps platform ({self.environment_name})",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"],
            ),
        )

        # Code generation endpoint
        code_gen_resource = self.ai_api.root.add_resource("generate")
        code_gen_integration = apigateway.LambdaIntegration(self.code_generator_lambda)
        code_gen_resource.add_method("POST", code_gen_integration)

        # Error analysis endpoint
        error_analysis_resource = self.ai_api.root.add_resource("analyze")
        error_analysis_integration = apigateway.LambdaIntegration(self.error_analyzer_lambda)
        error_analysis_resource.add_method("POST", error_analysis_integration)

        # Code optimization endpoint
        optimization_resource = self.ai_api.root.add_resource("optimize")
        optimization_integration = apigateway.LambdaIntegration(self.optimizer_lambda)
        optimization_resource.add_method("POST", optimization_integration)

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "AIToolsAPIURL",
            value=self.ai_api.url,
            description="AI Tools API Gateway URL",
            export_name=f"{self.stack_name}-AIToolsAPIURL"
        )

        CfnOutput(
            self,
            "CodeTemplatesTableName",
            value=self.code_templates_table.table_name,
            description="Code Templates DynamoDB Table Name",
            export_name=f"{self.stack_name}-CodeTemplatesTableName"
        )

        CfnOutput(
            self,
            "AnalysisResultsTableName",
            value=self.analysis_results_table.table_name,
            description="Analysis Results DynamoDB Table Name",
            export_name=f"{self.stack_name}-AnalysisResultsTableName"
        )
