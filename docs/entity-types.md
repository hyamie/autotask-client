# Autotask Entity Types

## Daily-Driver Entities (Hand-Crafted Models)

These have Pydantic models with typed fields in `src/autotask/models/`.

### Tickets (`Tickets`)
Primary work item. The most-used entity.

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| ticketNumber | str | Human-readable number |
| title | str | Required |
| description | str | |
| companyID | int | Required |
| queueID | int | See queue IDs below |
| status | int | See status IDs below |
| priority | int | See priority IDs below |
| assignedResourceID | int | |
| projectID | int | |
| createDate | datetime | Read-only |
| dueDateTime | datetime | |
| lastActivityDate | datetime | Read-only |
| source | int | |

### Companies (`Companies`)
Customer/vendor organizations.

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| companyName | str | Required |
| companyNumber | str | |
| companyType | int | |
| phone | str | |
| isActive | bool | |
| address1, address2 | str | |
| city, state, postalCode, country | str | |
| ownerResourceID | int | |

### Resources (`Resources`)
Users/technicians in the system.

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| firstName | str | |
| lastName | str | |
| email | str | |
| isActive | bool | |
| resourceType | str | |
| title | str | |

### Projects (`Projects`)

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| projectNumber | str | |
| projectName | str | Required |
| companyID | int | Required |
| projectType | int | |
| status | int | |
| startDateTime | datetime | |
| endDateTime | datetime | |
| projectLeadResourceID | int | |
| description | str | |
| organizationalLevelAssociationID | int | LOB |
| completedPercentage | int | |

### Tasks (`Tasks`) — Child of Projects

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| projectID | int | Parent ID (required) |
| title | str | Required |
| status | int | |
| priority | int | |
| assignedResourceID | int | |
| estimatedHours | float | |
| hoursWorked | float | Read-only |
| taskNumber | str | |
| sortOrder | int | |
| phaseID | int | |

### TimeEntries (`TimeEntries`)

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| ticketID | int | One of ticketID/taskID required |
| taskID | int | |
| resourceID | int | Required |
| dateWorked | datetime | Required |
| hoursWorked | float | Required |
| hoursToBill | float | |
| summaryNotes | str | |
| internalNotes | str | |
| roleID | int | |
| type | int | |
| billingCodeID | int | |
| showOnInvoice | bool | |

### Notes (ProjectNote, TaskNote, TicketNote)
All share the same base fields, differ by parent entity.

| Field | Type | Notes |
|-------|------|-------|
| id | int | Auto-generated |
| title | str | |
| description | str | Note content |
| noteType | int | |
| publish | int | Visibility |
| creatorResourceID | int | |
| createDateTime | datetime | Read-only |
| projectID/taskID/ticketID | int | Parent ID |

## Generic Entities (~200 types)

Any entity not listed above can be accessed generically via `EntityManager.query("EntityName", ...)` or `autotask query EntityName`. Returns raw dicts.

Common generic entities:
- `ConfigurationItems` — assets/devices
- `Contracts` — service contracts
- `ContractServices` — services on contracts
- `Invoices` — billing invoices
- `Opportunities` — sales pipeline
- `Contacts` — individual people at companies
- `ServiceCalls` — dispatched service visits
- `Phases` — project phases
- `BillingCodes` — time entry categorization

Use `autotask info EntityName` to check capabilities and `autotask fields EntityName` to discover fields.
