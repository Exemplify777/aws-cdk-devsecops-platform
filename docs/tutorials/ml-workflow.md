# Tutorial: Building an ML Workflow

This tutorial will guide you through creating a complete machine learning workflow using the DevSecOps Platform, from data preparation to model deployment and monitoring.

## What You'll Build

By the end of this tutorial, you'll have:

- A complete ML training and inference pipeline
- Model versioning and experiment tracking with MLflow
- Automated model deployment with A/B testing
- Model monitoring and drift detection
- CI/CD pipeline for ML workflows

## Prerequisites

- DevSecOps Platform installed and configured
- Basic understanding of machine learning concepts
- Python knowledge for model development
- AWS CLI configured with SageMaker permissions

## Step 1: Create ML Workflow Project

### Create the Project

Create a new ML workflow project:

```bash
ddk-cli create-project customer-churn-ml --template ml-workflow
```

Configure the template:
- **ML framework**: Choose `scikit-learn`
- **Instance type**: Choose `ml.m5.large`
- **Enable auto-scaling**: Choose `yes`
- **Enable model monitoring**: Choose `yes`
- **Deployment strategy**: Choose `blue-green`

### Explore the Project Structure

```bash
cd customer-churn-ml
tree -L 3
```

You'll see:
```
customer-churn-ml/
├── README.md
├── app.py                    # CDK application
├── data/
│   ├── raw/                 # Raw training data
│   ├── processed/           # Processed features
│   └── sample/              # Sample datasets
├── src/
│   ├── training/            # Model training code
│   ├── inference/           # Inference code
│   ├── preprocessing/       # Data preprocessing
│   └── monitoring/          # Model monitoring
├── models/                  # Trained model artifacts
├── notebooks/               # Jupyter notebooks
├── infrastructure/          # CDK infrastructure
└── tests/                   # Test files
```

## Step 2: Understand the ML Infrastructure

### Review the ML Stack

Examine `infrastructure/stacks/ml_workflow_stack.py`:

```python
class MLWorkflowStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 buckets for ML artifacts
        self.data_bucket = s3.Bucket(self, "MLDataBucket")
        self.model_bucket = s3.Bucket(self, "MLModelBucket")
        
        # SageMaker components
        self.training_job = sagemaker.CfnModel(self, "TrainingJob")
        self.endpoint_config = sagemaker.CfnEndpointConfig(self, "EndpointConfig")
        self.endpoint = sagemaker.CfnEndpoint(self, "ModelEndpoint")
        
        # MLflow tracking server
        self.mlflow_server = ecs.FargateService(self, "MLflowServer")
        
        # Step Functions for ML workflow
        self.ml_pipeline = stepfunctions.StateMachine(self, "MLPipeline")
```

### Key Components

The ML workflow includes:

1. **Data Storage**: S3 buckets for data and model artifacts
2. **Training Infrastructure**: SageMaker training jobs
3. **Model Registry**: MLflow for experiment tracking
4. **Inference Endpoints**: SageMaker endpoints for real-time inference
5. **Monitoring**: CloudWatch and custom metrics for model monitoring
6. **Orchestration**: Step Functions for workflow management

## Step 3: Prepare Your Data

### Upload Training Data

Upload your training dataset:

```bash
# Upload training data
aws s3 cp data/raw/customer_data.csv s3://customer-churn-ml-data-dev-123456789012/raw/

# Or use sample data
cp data/sample/churn_sample.csv data/raw/customer_data.csv
aws s3 cp data/raw/customer_data.csv s3://customer-churn-ml-data-dev-123456789012/raw/
```

### Data Preprocessing

Review the preprocessing code in `src/preprocessing/preprocess.py`:

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder

def preprocess_data(input_path, output_path):
    """Preprocess customer churn data."""
    
    # Load data
    df = pd.read_csv(input_path)
    
    # Handle missing values
    df = df.dropna()
    
    # Feature engineering
    df['tenure_months'] = df['tenure']
    df['monthly_charges_scaled'] = StandardScaler().fit_transform(
        df[['MonthlyCharges']]
    )
    
    # Encode categorical variables
    le = LabelEncoder()
    categorical_columns = ['gender', 'Partner', 'Dependents']
    for col in categorical_columns:
        df[f'{col}_encoded'] = le.fit_transform(df[col])
    
    # Save processed data
    df.to_csv(output_path, index=False)
    
    return df
```

### Run Preprocessing

Execute the preprocessing step:

```bash
# Run preprocessing locally
python src/preprocessing/preprocess.py \
  --input data/raw/customer_data.csv \
  --output data/processed/features.csv

# Upload processed data
aws s3 cp data/processed/features.csv s3://customer-churn-ml-data-dev-123456789012/processed/
```

## Step 4: Deploy ML Infrastructure

### Deploy the Stack

Deploy your ML infrastructure:

```bash
ddk-cli deploy --env dev
```

This creates:
- S3 buckets for data and models
- SageMaker training and inference infrastructure
- MLflow tracking server
- Step Functions workflow
- CloudWatch monitoring

### Verify Deployment

```bash
# Check deployment status
ddk-cli status --env dev

# Verify MLflow server
curl https://mlflow.customer-churn-ml-dev.company.com/health
```

## Step 5: Train Your Model

### Review Training Code

Examine `src/training/train.py`:

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score

def train_model(data_path, model_output_path):
    """Train customer churn prediction model."""
    
    # Start MLflow run
    with mlflow.start_run():
        # Load data
        df = pd.read_csv(data_path)
        X = df.drop(['Churn'], axis=1)
        y = df['Churn']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        
        # Log metrics
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        
        # Log model
        mlflow.sklearn.log_model(model, "model")
        
        # Save model
        joblib.dump(model, model_output_path)
        
        return model, accuracy
```

### Start Training Job

Trigger the training workflow:

```bash
# Start training via Step Functions
ddk-cli execute --env dev --workflow training

# Or run training directly
python src/training/train.py \
  --data-path data/processed/features.csv \
  --model-output models/churn_model.pkl
```

### Monitor Training

```bash
# Check training status
ddk-cli executions --env dev --workflow training

# View training logs
ddk-cli logs --env dev --service training --follow

# Check MLflow experiments
open https://mlflow.customer-churn-ml-dev.company.com
```

## Step 6: Model Evaluation and Validation

### Review Model Performance

Check the model performance in MLflow:

1. Open MLflow UI
2. Navigate to the experiment
3. Compare different runs
4. Review metrics and artifacts

### Model Validation

Run model validation tests:

```bash
# Run model validation
python src/validation/validate_model.py \
  --model-path models/churn_model.pkl \
  --test-data data/processed/test_features.csv

# Check validation results
ddk-cli metrics --env dev --metric ModelAccuracy
```

### A/B Testing Setup

Configure A/B testing for model comparison:

```python
# src/inference/ab_testing.py
class ABTestingConfig:
    def __init__(self):
        self.model_a_weight = 0.8  # 80% traffic to model A
        self.model_b_weight = 0.2  # 20% traffic to model B
        self.metrics_to_track = [
            'prediction_accuracy',
            'response_time',
            'business_impact'
        ]
```

## Step 7: Deploy Model to Staging

### Create Model Endpoint

Deploy the model to SageMaker endpoint:

```bash
# Deploy model to staging
ddk-cli deploy --env staging --component model-endpoint

# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name customer-churn-ml-staging
```

### Test Model Inference

Test the deployed model:

```bash
# Test inference endpoint
python src/inference/test_endpoint.py \
  --endpoint-name customer-churn-ml-staging \
  --test-data data/sample/inference_sample.json

# Load test the endpoint
python src/testing/load_test.py \
  --endpoint-name customer-churn-ml-staging \
  --requests-per-second 10 \
  --duration 300
```

### Validate Staging Deployment

```bash
# Run staging validation
ddk-cli test --env staging --type integration

# Check model performance metrics
ddk-cli metrics --env staging --metric ModelLatency
ddk-cli metrics --env staging --metric PredictionAccuracy
```

## Step 8: Production Deployment

### Pre-Production Checklist

Before production deployment:

- [ ] Model performance meets requirements
- [ ] Load testing completed successfully
- [ ] Security scanning passed
- [ ] Model monitoring configured
- [ ] Rollback plan prepared

### Blue-Green Deployment

Deploy to production using blue-green strategy:

```bash
# Deploy new model version (green)
ddk-cli deploy --env prod --strategy blue-green --version 2.0

# Monitor green deployment
ddk-cli status --env prod --deployment green

# Switch traffic to green
ddk-cli switch-traffic --env prod --target green --percentage 100

# Remove blue deployment
ddk-cli cleanup --env prod --deployment blue
```

### Canary Deployment Alternative

Or use canary deployment:

```bash
# Deploy canary version
ddk-cli deploy --env prod --strategy canary --version 2.0

# Gradually increase traffic
ddk-cli shift-traffic --env prod --canary-percentage 10
ddk-cli shift-traffic --env prod --canary-percentage 50
ddk-cli shift-traffic --env prod --canary-percentage 100

# Finalize deployment
ddk-cli finalize-deployment --env prod
```

## Step 9: Model Monitoring

### Set Up Model Monitoring

Configure comprehensive model monitoring:

```python
# src/monitoring/model_monitor.py
class ModelMonitor:
    def __init__(self, endpoint_name):
        self.endpoint_name = endpoint_name
        self.metrics = [
            'prediction_drift',
            'data_drift',
            'model_accuracy',
            'response_time'
        ]
    
    def check_data_drift(self, reference_data, current_data):
        """Detect data drift using statistical tests."""
        # Implementation for data drift detection
        pass
    
    def check_model_drift(self, predictions, actuals):
        """Detect model performance drift."""
        # Implementation for model drift detection
        pass
```

### Configure Alerts

Set up monitoring alerts:

```bash
# Configure model performance alerts
ddk-cli alerts --env prod \
  --metric ModelAccuracy \
  --threshold 0.85 \
  --comparison less-than \
  --email ml-team@company.com

# Configure data drift alerts
ddk-cli alerts --env prod \
  --metric DataDrift \
  --threshold 0.1 \
  --comparison greater-than \
  --slack-webhook https://hooks.slack.com/services/...
```

### Monitor Model Performance

```bash
# View model metrics
ddk-cli metrics --env prod --service model-endpoint

# Check for drift
python src/monitoring/drift_detection.py \
  --endpoint-name customer-churn-ml-prod \
  --reference-period 7d

# Generate monitoring report
ddk-cli report --env prod --type model-monitoring --period weekly
```

## Step 10: Model Retraining

### Automated Retraining

Set up automated retraining triggers:

```python
# src/retraining/auto_retrain.py
class AutoRetraining:
    def __init__(self):
        self.retrain_triggers = [
            'accuracy_below_threshold',
            'data_drift_detected',
            'scheduled_weekly'
        ]
    
    def should_retrain(self):
        """Check if model should be retrained."""
        # Check various conditions
        return True  # or False
    
    def trigger_retraining(self):
        """Trigger retraining workflow."""
        # Start Step Functions workflow
        pass
```

### Manual Retraining

Trigger manual retraining when needed:

```bash
# Start retraining workflow
ddk-cli execute --env prod --workflow retraining

# Monitor retraining progress
ddk-cli executions --env prod --workflow retraining

# Compare new model with current
python src/evaluation/compare_models.py \
  --current-model models/churn_model_v1.pkl \
  --new-model models/churn_model_v2.pkl
```

## Step 11: MLOps Best Practices

### Version Control

Manage model versions effectively:

```bash
# Tag model version
git tag -a v2.0 -m "Customer churn model v2.0"
git push origin v2.0

# Register model in MLflow
python src/registry/register_model.py \
  --model-name customer-churn \
  --version 2.0 \
  --stage Production
```

### Experiment Tracking

Track all experiments systematically:

```python
# Enhanced experiment tracking
with mlflow.start_run(run_name=f"experiment_{datetime.now()}"):
    # Log hyperparameters
    mlflow.log_params({
        'n_estimators': 100,
        'max_depth': 10,
        'feature_selection': 'recursive'
    })
    
    # Log metrics
    mlflow.log_metrics({
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score
    })
    
    # Log artifacts
    mlflow.log_artifact('feature_importance.png')
    mlflow.log_artifact('confusion_matrix.png')
```

### Model Governance

Implement model governance practices:

```bash
# Model approval workflow
ddk-cli model approve --model customer-churn --version 2.0 --approver ml-lead

# Model documentation
ddk-cli model document --model customer-churn --version 2.0 \
  --description "Improved churn prediction with new features"

# Compliance check
ddk-cli compliance --framework ML-GOVERNANCE --model customer-churn
```

## Troubleshooting

### Common Issues

#### 1. Training Job Failures

```bash
# Check training logs
aws logs tail /aws/sagemaker/TrainingJobs/customer-churn-training --follow

# Debug training script
python src/training/train.py --debug --local-mode
```

#### 2. Endpoint Deployment Issues

```bash
# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name customer-churn-ml-prod

# Review endpoint logs
aws logs tail /aws/sagemaker/Endpoints/customer-churn-ml-prod --follow
```

#### 3. Model Performance Degradation

```bash
# Check model metrics
ddk-cli metrics --env prod --metric ModelAccuracy --period 7d

# Run drift analysis
python src/monitoring/drift_analysis.py --detailed
```

## Next Steps

Enhance your ML workflow with:

1. **Advanced Monitoring**: Implement custom model monitoring metrics
2. **Feature Store**: Set up a feature store for feature reuse
3. **Multi-Model Endpoints**: Deploy multiple models on single endpoint
4. **Real-time Features**: Add real-time feature computation
5. **AutoML**: Integrate automated machine learning capabilities

## Additional Resources

- [SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [ML Security Guide](../security/ml-security.md)
- [Model Monitoring Best Practices](../operations/ml-monitoring.md)

Congratulations! You've built a complete MLOps workflow with the DevSecOps Platform! 🚀
