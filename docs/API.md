# QuoteFlow Pro — REST API Reference Documentation

QuoteFlow Pro provides a full RESTful JSON API under `/api/v1/` for managing proposals, processing site-walk notes, searching pricing catalog items, exporting CSV reports, and integrating with external CRMs.

---

## Interactive Documentation

- **Swagger UI**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **ReDoc**: [`http://localhost:8000/redoc`](http://localhost:8000/redoc)
- **OpenAPI JSON Spec**: [`http://localhost:8000/openapi.json`](http://localhost:8000/openapi.json)

---

## Authentication & Headers

Currently, internal requests utilize session context. For external client integrations, pass standard HTTP headers:

```http
Content-Type: application/json
X-Request-ID: <optional-uuid-correlation-id>
```

---

## Base URL
```
http://localhost:8000/api/v1
```

---

## Endpoints

### 1. List Proposals
Retrieve all proposals in descending order of creation date.

- **URL**: `GET /api/v1/proposals`
- **Response**: `200 OK`

---

### 2. Export Proposals as CSV
Download a CSV export file of all proposal pipeline data.

- **URL**: `GET /api/v1/proposals/export/csv`
- **Response**: `200 OK` (`text/csv` attachment)

---

### 3. Parse Notes & Draft Proposal
Parse raw site-walk notes using Gemini 3.6 Flash and store a structured draft.

- **URL**: `POST /api/v1/proposals/parse`
- **Request Body**:
```json
{
  "client_name": "Smith Residence",
  "raw_notes": "Front yard sod installation ~1200 sqft, hedge trimming 50ft linear."
}
```

---

### 4. Get Proposal Details
Fetch a single proposal by ID.

- **URL**: `GET /api/v1/proposals/{id}`

---

### 5. Update Proposal Line Items & Details
Update line items, quantities, pricing, or client metadata for a proposal draft.

- **URL**: `PUT /api/v1/proposals/{id}`

---

### 6. Approve Proposal
Approve a draft proposal and fire Slack notification and team webhooks.

- **URL**: `POST /api/v1/proposals/{id}/approve`

---

### 7. Reject Proposal
Mark a draft proposal as rejected.

- **URL**: `POST /api/v1/proposals/{id}/reject`

---

### 8. Delete Proposal
Delete a proposal record from the database.

- **URL**: `DELETE /api/v1/proposals/{id}`

---

### 9. Get Pricing Catalog
Retrieve the list of 200+ pricing catalog items.

- **URL**: `GET /api/v1/catalog`

---

### 10. GoHighLevel (GHL) CRM Integration Webhook
Simulated GoHighLevel CRM synchronization webhook trigger.

- **URL**: `POST /api/v1/integrations/ghl/webhook`
```json
{
  "event": "proposal_approved",
  "proposal_id": 1
}
```
