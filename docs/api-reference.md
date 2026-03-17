# Autotask REST API Reference

Quick reference for Claude Code when working with the Autotask API.

## Authentication

- Header-based: `UserName`, `Secret`, `ApiIntegrationCode`, `Content-Type: application/json`
- Optional: `ImpersonationResourceId`
- Invalid creds return HTTP **500** (not 401) — the client detects auth-related 500s
- Zone discovery required before first call: `GET https://webservices.autotask.net/atservicesrest/v1.0/zoneInformation?user=<email>`
- Our tenant zone: `webservices24.autotask.net`

## Rate Limits

- **10,000 requests/hour** shared across ALL integrations on the account
- Response headers: `X-RateLimit-Current`, `X-RateLimit-Limit`
- Progressive throttling: 50% → 0.5s delay, 75% → 1s delay
- **500 records max** per query response
- **3 concurrent threads** per endpoint
- Attachments: 6-7 MB per file, 10 MB per 5-min window

## Query Syntax

POST to `/{Entity}/query` with JSON body:

```json
{
  "filter": [
    {"field": "status", "op": "eq", "value": 8},
    {"field": "id", "op": "gt", "value": 0}
  ]
}
```

### Operators

| Operator | Description |
|----------|-------------|
| eq | Equals |
| noteq | Not equals |
| gt | Greater than |
| gte | Greater than or equal |
| lt | Less than |
| lte | Less than or equal |
| beginsWith | String starts with |
| endsWith | String ends with |
| contains | String contains |
| exist | Field is not null |
| notExist | Field is null |
| in | Value in list |
| notIn | Value not in list |

### UDF Filters

Add `"udf": true` to filter on user-defined fields. **Only ONE UDF filter per query.**

### Pagination

API returns max 500 records. Paginate with `id > last_id`:

```json
{"field": "id", "op": "gt", "value": 12345}
```

The client's `query_all()` handles this automatically.

## CRUD Operations

| Method | Use | Safety |
|--------|-----|--------|
| GET `/{Entity}/{id}` | Read single | Safe |
| POST `/{Entity}` | Create | — |
| POST `/{Entity}/query` | Query/search | Safe |
| PATCH `/{Entity}` | Partial update | **Safe — only changes specified fields** |
| PUT `/{Entity}` | Full update | **DANGEROUS — nulls unspecified fields** |
| DELETE `/{Entity}/{id}` | Delete | — |

**ALWAYS use PATCH, never PUT.** PUT will null every field you don't include.

## Entity Metadata (Self-Describing API)

- `GET /{Entity}/entityInformation` — capabilities (canCreate, canDelete, canQuery, canUpdate)
- `GET /{Entity}/entityInformation/fields` — field types, required, read-only, picklists
- `GET /{Entity}/entityInformation/userDefinedFields` — UDF definitions

## Child Entities

Some entities require parent ID in the URL path:

| Child Entity | Parent | URL Pattern |
|-------------|--------|-------------|
| Tasks | Projects | `/Projects/{id}/Tasks` |
| ProjectNotes | Projects | `/Projects/{id}/ProjectNotes` |
| TaskNotes | Tasks | `/Tasks/{id}/TaskNotes` |
| TicketNotes | Tickets | `/Tickets/{id}/TicketNotes` |

## Gotchas

1. **Silent permission failures** — empty results instead of errors when missing permissions
2. **UDFs missing from response** when no values have been set on the entity
3. **No call batching** — each operation is a separate HTTP request
4. **Rich text not supported** via API
5. **Password expiry** can silently break API users
6. **Zone URL must be discovered** — cannot hardcode (though we cache it)

## Webhooks (Limited)

Only 5 entity types support webhooks:
- Companies, Contacts, ConfigurationItems, Tickets, TicketNotes
- 1,500 callouts per rolling hour per entity
- 1-5 minute latency
