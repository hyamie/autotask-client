# Autotask Picklist IDs

Known picklist values for our tenant. Use these when filtering or creating entities.

## Ticket Status IDs

| ID | Status |
|----|--------|
| 1 | New |
| 5 | Complete |
| 7 | Waiting Customer |
| 8 | In Progress |
| 9 | Waiting Materials |
| 10 | Dispatched |
| 12 | Waiting Vendor |
| 17 | On Hold |
| 19 | Customer Note Added |
| 20 | RMM Resolved |
| 21 | Referred to LEC |
| 22 | Duplicate |
| 23 | Canceled |
| 25 | Escalate to Billing |
| 26 | Scheduled |
| 27 | Mike Order Equipment |
| 28 | Requested |
| 29 | Quoted |
| 30 | Approved |
| 31 | Ordered |
| 32 | Received |

## Ticket Priority IDs

| ID | Priority |
|----|----------|
| 1 | High |
| 2 | Medium |
| 3 | Low |
| 4 | Critical |

## Queue IDs

Use `autotask fields Tickets` to get full current list. Common queues include:
- Client Portal
- MSP Helpdesk
- Level II Support
- Engineering Support
- Projects

(19 queues defined — exact IDs are tenant-specific, use `autotask fields Tickets` and look for `queueID` picklist values)

## Line of Business (LOB) Mappings

| Abbreviation | LOB ID |
|-------------|--------|
| CIT | 17 |
| CA | 18 |
| GA | 19 |
| NITH | 20 |

LOB is set via `organizationalLevelAssociationID` on Projects and Tickets.

## Template Company IDs

These are internal/template companies to exclude from customer queries:
- 0, 264, 296
