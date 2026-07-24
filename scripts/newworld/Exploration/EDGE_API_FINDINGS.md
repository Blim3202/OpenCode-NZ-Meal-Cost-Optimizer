# New World Edge API Exploration

## Summary

The New World Edge API at `https://api-prod.newworld.co.nz/v1/edge/` **partially works** but is **not a replacement for the mobile API**.

## What Works

### Store Listing (`GET /v1/edge/store/physical`)
- **Status**: ✅ Works (HTTP 200)
- **Requirement**: Must provide BOTH headers:
  - `Authorization: Bearer {mobile_api_token}`
  - `access_token: {mobile_api_token}`
- **Result**: Returns 149 stores with identical data to mobile API (same UUIDs, coordinates, names)

## What Doesn't Work

### Product Search
All product endpoints return **HTTP 404**:
- `GET /v1/edge/products/search?q=milk&storeId={id}`
- `GET /v1/edge/products?storeId={id}&q=milk`
- `GET /v1/edge/ecomm-products/MNW/{storeId}/search?q=milk`
- `GET /v1/edge/store/{storeId}/products/search?q=milk`
- `GET /v1/edge/search?q=milk&storeId={id}`
- `GET /v1/edge/products`
- `GET /v1/edge/ecomm-products`
- `GET /v1/edge/categories`
- All POST variants also 404

## The JWT Token

The mobile API guest token is a valid JWT:
```json
{
  "jti": "uuid",
  "iss": "online-customer",
  "sessionId": "uuid",
  "banner": "MNW",
  "firstName": "anonymous",
  "email": "anonymous",
  "roles": ["ANONYMOUS"],
  "exp": timestamp
}
```

- **Issuer**: `online-customer` (shared IdP)
- **Banner**: `MNW` (New World)
- **Roles**: `["ANONYMOUS"]` — guest user
- **Validity**: 30 minutes (1800 seconds)

## Why the Mobile Token Works on Edge API

Both APIs are behind the same Apigee gateway and trust the same IdP (`online-customer`). The `JWT-VerifyRetailEdgeToken` policy validates the JWT signature and issuer — the mobile token passes because it's from the same IdP.

## Without Valid Token

| Request | Result |
|---------|--------|
| No headers | 403 (Cloudflare challenge) |
| `x-requested-with: ??` | 401 (JWT policy: `Failed to Resolve Variable`) |
| `Authorization: Bearer fake` | 403 (Cloudflare) |
| `Authorization + access_token fake` | 403 (Cloudflare) |

The 401 with `x-requested-with` bypasses Cloudflare but hits the Apigee JWT policy which rejects invalid/missing tokens.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  Mobile App     │     │  New World Web   │
│  (Android/iOS)  │     │  (Next.js)       │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│         Apigee Gateway                  │
│  (api-prod.newworld.co.nz)              │
│  ┌─────────────────┐ ┌───────────────┐  │
│  │ Edge API        │ │ Mobile API    │  │
│  │ /v1/edge/...    │ │ /prod/mobile/ │  │
│  │ JWT-Verify      │ │ JWT-Verify    │  │
│  └────────┬────────┘ └──────┬────────┘  │
└───────────┼─────────────────┼────────────┘
            │                 │
            ▼                 ▼
    ┌───────────────┐ ┌───────────────┐
    │ Store Listing │ │ Store Listing │
    │ (149 stores)  │ │ (149 stores)  │
    │ NO Products   │ │ PRODUCTS ✓    │
    └───────────────┘ └───────────────┘
```

## Conclusion

**The Edge API cannot replace the mobile API** for the meal cost optimizer because:

1. **No product search endpoints exist** on the Edge API
2. **Per-store pricing requires product search** — the core of the optimizer
3. The mobile API provides identical store data PLUS full product search with per-store pricing

## Recommendation

Continue using the Foodstuffs mobile API (`api-prod.prod.fsniwaikato.kiwi/prod`) for all New World operations:
- Guest auth: `POST /mobile/user/login/guest` with `{"banner": "MNW"}`
- Store listing: `GET /mobile/store/physical`
- Product search: `POST /mobile/ecomm-products/MNW/{storeId}/search?q={query}`

The Edge API exploration confirms the mobile API is the correct and only viable path.

---

*Exploration completed: 2025-07-24*
*Scripts: `scripts/newworld/Exploration/explore_edge_api.py`*