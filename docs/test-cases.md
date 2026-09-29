# Manual acceptance test checklist

| ID | Scenario | Input/action | Expected result |
|---|---|---|---|
| TC01 | Register | New valid email and 12+ character password | Account created, bearer token returned |
| TC02 | Bad auth | Missing token or wrong password | 401; private device data stays hidden |
| TC03 | Device isolation | User B requests User A's device | 404 with no data disclosure |
| TC04 | Device identity | Sensor submits missing/incorrect key | 401, no reading persisted |
| TC05 | Simulator values | Generate a reading | Ranges valid, timestamp UTC, values drift gradually |
| TC06 | Invalid value | Soil 101, NaN, temperature 90 | 422 and no DB write |
| TC07 | Invalid time | No timezone, >5 min future, >7 days old | 422 |
| TC08 | Duplicate delivery | Replay same device/event ID | Accepted as duplicate; no second reading/action |
| TC09 | Latest/history | Submit valid values then fetch | Latest and ordered bounded history returned |
| TC10 | Dry plant | Reading below active threshold | One watering action queued and warning alert recorded |
| TC11 | Moist plant | Reading >= threshold | No automatic watering |
| TC12 | Cooldown | Second dry reading inside five minutes | No additional action |
| TC13 | Reservoir safety | Tank <=5% and dry soil | Watering blocked; critical low tank alert |
| TC14 | Pulse limit | Request >10 second manual pulse | Validation rejects it; firmware action stays bounded |
| TC15 | Manual control | Owner requests pulse with fresh reading | One event queued |
| TC16 | Offline device | Wait longer than configured interval | Device marked offline and warning shown |
| TC17 | Alert resolution | Moisture recovers / user acknowledges | Active alert acknowledged; dashboard refreshes |
| TC18 | Database unavailable | Stop local database/API dependency | Health endpoint returns 503 or request error is clear |
| TC19 | API retry | Temporarily disconnect API then restore | Simulator logs retry and resumes after backoff |
| TC20 | Multiple plants | Add two device IDs under one owner | Independent thresholds, data, status, and history |
| TC21 | Threshold config | Set value outside 5–90% | 422, prior setting unchanged |
| TC22 | Auto mode | Turn automation off with dry reading | Reading stored; no automatic event |

## Automated run result

**Result on 2026-09-28:** 12 API tests passed. The dashboard production build completed successfully. A live simulator cycle also uploaded a synthetic sample, polled a queued action, and applied the virtual watering response. Manual browser acceptance beyond the locally seeded dashboard was not run as a separate E2E suite.
