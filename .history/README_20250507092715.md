# City of London Planning Scraper

A serverless application that scrapes planning application data from the City of London planning portal and provides it in JSON or CSV format.

## Features

- Web interface for easy data retrieval
- REST API endpoints for programmatic access
- Filter by month and ward
- Export data in CSV or JSON format
- Deployed as a serverless application on Vercel

## Deployment

### Deploy to Vercel

You can deploy this application to Vercel with a single click:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyourusername%2Fcity-of-london-planning-scraper)

### Manual Deployment

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/city-of-london-planning-scraper.git
   cd city-of-london-planning-scraper
   ```

2. Install Vercel CLI:
   ```
   npm install -g vercel
   ```

3. Login to Vercel:
   ```
   vercel login
   ```

4. Deploy the application:
   ```
   vercel
   ```

## API Endpoints

- `GET /` - Web interface
- `GET /api` - API information
- `GET /api/wards` - List all available wards
- `GET /api/months` - List available months
- `POST /api/scrape` - Run the scraper with specific parameters

### Scraper API

Send a POST request to `/api/scrape` with the following JSON body:

```json
{
  "start_month": "Jan 24",
  "end_month": "Feb 24",
  "selected_wards": ["ward_value1", "ward_value2"],
  "format": "json"  // or "csv"
}
```

The API will return either a JSON response with the scraped data or a CSV file for download, depending on the requested format.

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the development server:
   ```
   vercel dev
   ```

## Limitations

- To prevent timeouts on serverless functions, the API limits results to a maximum of 2 months and 3 wards per request.
- The scraper uses a delay between requests to avoid overloading the planning portal server.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 