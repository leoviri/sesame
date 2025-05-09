# City of London Planning Scraper API

A simple API that scrapes planning application data from the City of London planning portal and provides it in JSON or CSV format.

## API Endpoints

- `GET /api` - API information
- `POST /api/scrape` - Run the scraper with specific parameters

## API Usage

To get data from the scraper, send a POST request to `/api/scrape` with the following JSON body:

```json
{
  "start_month": "Mar 24",  // Optional: Format is "MMM YY" like "Mar 24" for March 2024
  "end_month": "Apr 24",    // Optional: Format is "MMM YY"
  "selected_wards": ["00000005", "00000006"],  // Optional: List of ward IDs
  "format": "csv"  // Optional: "json" (default) or "csv"
}
```

### Response

For JSON format, the response will be:

```json
{
  "data": [
    {
      "address": "123 Example Street, London",
      "name": "John Smith",
      "email": "john.smith@example.com"
    },
    // More records...
  ],
  "count": 25,
  "months": ["Mar 24", "Apr 24"],
  "wards": ["Bishopsgate", "Portsoken"]
}
```

For CSV format, the response will be a CSV file download with headers: "Address", "Name", "Email".

## Limitations

- To prevent timeouts, the API limits results to a maximum of 2 months and 3 wards per request.
- The scraper filters out emails ending with ".gov" and containing "tree".
- Due to serverless function limitations, large requests may time out.

## Example cURL Request

```bash
curl -X POST https://your-api-url.vercel.app/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_month":"Mar 24","end_month":"Apr 24","selected_wards":["00000005"],"format":"csv"}' \
  --output cityoflondon_data.csv
``` 