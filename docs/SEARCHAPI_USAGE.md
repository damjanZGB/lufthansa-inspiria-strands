# SearchAPI Usage

All Inspiria agents must go directly to [SearchAPI](https://www.searchapi.io/docs) using the Strands
`http_request` tool. Never call the legacy Render proxy or Bedrock action-group tools.

## Common Rules
- Base URL: `https://www.searchapi.io/api/v1/search`
- HTTP method: `GET`
- Header: `Authorization: Bearer hq1ZEvCm7Ftu88ubxZMyHAPj`
- Default query params: `hl=en`, `gl=DE`, `currency=EUR`
- Always include `included_airlines=LH,LX,OS,SN,EW,4Y,EN`

## Engines

### 1. Google Flights (`engine=google_flights`)
| Param | Description |
|-------|-------------|
| `departure_id` | IATA code or `/m/...` kgmid |
| `arrival_id` | Destination IATA/kgmid |
| `outbound_date` | `YYYY-MM-DD` |
| `return_date` | optional, `YYYY-MM-DD` |
| `travel_class` | `economy`, `business`, `first` |
| `stops` | `any` or `nonstop` |
| `adults` | Traveller count |

### 2. Google Flights Calendar (`engine=google_flights_calendar`)
| Param | Description |
|-------|-------------|
| `departure_id`, `arrival_id` | Same as above |
| `start_date`, `end_date` | ISO dates delimiting the flexible window |
| `travel_class`, `stops`, `adults` | Same semantics as flights |

### 3. Google Travel Explore (`engine=google_travel_explore`)
| Param | Description |
|-------|-------------|
| `departure_id` | Origin airport |
| `time_period` | Token such as `one_week_trip_in_march_2026` |
| `travel_mode` | Always `flights_only` |
| `arrival_id` | optional (if user fixed destination) |
| `interests` | optional, comma-delimited |
| `adults` | optional |

Agents should build these requests manually and send them through `http_request`. Capture the raw JSON
response and pass it back to the supervisor so it can render Lufthansa-branded answers.
