# Microservice Consistency Testing

This document provides instructions for testing the consistency between the external microservice and the existing internal transformation logic.

## Quick Start - One Button Testing

### Prerequisites

1. **Main ETL System Running**:
   ```bash
   cd /Users/trentcharlton/Documents/CloudWarriors/etl_prism_poc
   docker-compose up -d backend
   ```

2. **Microservice Running**:
   ```bash
   cd /Users/trentcharlton/Documents/CloudWarriors/zoom-platform-microservice
   docker-compose up -d
   ```

3. **Data Migration Complete**:
   ```bash
   python3 scripts/migrate_job_data.py
   ```

### Run All Tests (One Button)

```bash
# Test all job types (1297-1301)
./scripts/test_microservice_consistency.py

# Test specific job types
./scripts/test_microservice_consistency.py --job-ids 1297,1298

# Interactive mode (fix until perfect)
./scripts/test_microservice_consistency.py --interactive
```

## Test Process Overview

The testing framework automatically:

1. **Setup Phase**:
   - Authenticates with superuser credentials
   - Gets dynamic IDs for SSOT schemas and loaders
   - Resets job statuses to 'failed'
   - Clears previous test data

2. **Path A Testing** (Internal):
   - Sets platform integration_mode to 'internal' 
   - Runs transformation using existing zoom_transformer_helper.py
   - Captures output data

3. **Path B Testing** (Microservice):
   - Sets platform integration_mode to 'microservice'
   - Runs transformation using external microservice
   - Captures output data

4. **Comparison Analysis**:
   - Deep diff comparison of outputs
   - Field-by-field analysis
   - Business logic validation
   - Severity assessment (critical/warning/info)

5. **Reporting**:
   - Console output with immediate results
   - Detailed JSON report saved to file
   - Fix suggestions for each difference

## Job Types Tested

| Job ID | Job Type | Description | Platform Mapping |
|--------|----------|-------------|------------------|
| 1297 | 33 | Sites | RingCentral → Zoom Sites |
| 1298 | 39 | Users | RingCentral → Zoom Users |
| 1299 | 45 | Call Queues | RingCentral → Zoom Call Queues |
| 1300 | 77 | Auto Receptionists | RingCentral → Zoom ARs |
| 1301 | 78 | IVR | RingCentral → Zoom IVR |

## Understanding Test Results

### Success Output
```
✅ Job 1297 (Sites): IDENTICAL
✅ Job 1298 (Users): IDENTICAL  
✅ Job 1299 (Call Queues): IDENTICAL
✅ Job 1300 (Auto Receptionists): IDENTICAL
✅ Job 1301 (IVR): IDENTICAL

🎉 All tests passed! Microservice is consistent with internal implementation.
```

### Failure Output
```
❌ Job 1297 (Sites): DIFFERENT
  Differences: 2 categories
    - values_changed: 3 items
    - dictionary_item_removed: 1 items

Fix suggestions:
  - default_emergency_address.country: Check country code conversion (full name vs ISO code)
  - site_code: Case sensitivity difference - check string handling
```

## Detailed Comparison Features

### Field-by-Field Analysis
- **Exact Match**: Fields must be identical
- **Tolerance Handling**: Ignores timestamps, UUIDs, system IDs
- **Type Validation**: Ensures data types match
- **Business Logic**: Validates transformation rules

### Smart Diff Categories
- **Critical**: Differences that would break functionality
- **Warning**: Important differences that should be reviewed
- **Info**: Minor differences (case, formatting, etc.)

### Fix Suggestions
The engine provides specific suggestions for each difference:
- **Address Issues**: Country code format, zip code patterns
- **Timezone Issues**: IANA format validation
- **User Type Mapping**: Zoom user type code validation
- **IVR Actions**: Key and action code mapping validation

## Interactive Fix Loop

When using `--interactive` mode:

1. **Run Tests**: Execute comparison for all job types
2. **Show Results**: Display detailed diff report
3. **Wait for Fixes**: Pause execution for code fixes
4. **Re-run Tests**: Automatically retry after fixes
5. **Repeat**: Continue until all tests pass

Example workflow:
```bash
./scripts/test_microservice_consistency.py --interactive

# Output shows differences in job 1297
# Fix the microservice transformer code
# Press Enter to continue
# Tests re-run automatically
# Repeat until perfect consistency
```

## Troubleshooting

### Authentication Issues
```bash
# Verify superuser exists
docker-compose exec backend python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.filter(email='admin@test.com').first()
```

### Database Connection Issues
```bash
# Check database connectivity
docker-compose exec backend python manage.py dbshell
```

### Microservice Connection Issues  
```bash
# Test microservice health
curl http://localhost:3555/health

# Check logs
docker-compose logs microservice
```

### Platform Integration Mode Issues
```bash
# Verify platform settings
docker-compose exec backend python manage.py shell
>>> from api.models import PhonePlatform
>>> PhonePlatform.objects.filter(id__in=[2,3]).values('id', 'name', 'integration_mode', 'mcp_server_url')
```

## Manual Testing Commands

If you need to run individual steps manually:

### Reset Job Status
```bash
curl -X POST http://127.0.0.1:8030/api/etl/reset-job/ \
  -H "Content-Type: application/json" \
  -d '{"job_id": 1297, "status": "failed"}'
```

### Transform Data (Internal Path)
```bash
curl -X POST http://127.0.0.1:8030/api/etl/transform-data/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "job_id": 1297,
    "source_platform_id": 4,
    "job_type": 33,
    "ssot_schema_id": 67
  }'
```

### Transform Data (Microservice Path)
```bash
# First set platform to microservice mode, then run same transform command
```

## Performance Metrics

The test framework tracks:
- **Processing Time**: Time taken for each transformation
- **Record Count**: Number of records processed
- **Accuracy Percentage**: % of identical records
- **Difference Count**: Total field differences found

## Continuous Integration

For CI/CD integration:

```bash
# Exit code 0 = success, 1 = failure
./scripts/test_microservice_consistency.py
echo $?  # Check exit code
```

## Support

If tests fail consistently:

1. **Check Logs**: Review both main system and microservice logs
2. **Review Implementation**: Compare microservice code with zoom_transformer_helper.py
3. **Validate Data**: Ensure test data is consistent between runs
4. **Update Tests**: Modify tolerance settings if needed for acceptable differences