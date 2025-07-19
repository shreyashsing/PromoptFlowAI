# Bug Tracking for PromptFlow AI

## Bug Log:
| ID  | Title                      | Status | Severity | Reported On | Description | Resolution |
|-----|----------------------------|--------|----------|-------------|-------------|------------|
| B01 | API key validation failure | Open   | High     | 2025-07-13  | Invalid SerpAPI key causes 401 error | Add input validation before API call |
| B02 | Email formatting issue     | Closed | Low      | 2025-07-12  | Email body lacks line breaks | Fixed by adding `\n` in send_email.py |

## Bug Report Format:
### Bug ID: [BXX]
**Title**: [Short description]  
**Status**: [Open/Closed/In Progress]  
**Severity**: [Low/Medium/High]  
**Reported On**: [YYYY-MM-DD]  
**Description**: [Detailed explanation, steps to reproduce]  
**Resolution**: [How it was fixed or planned fix]

## Notes:
- Update this table for every bug encountered during development or execution.
- log bugs by appending to this file.
- Reference this file when debugging, per `workflow.txt`.