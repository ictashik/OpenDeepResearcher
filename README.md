# OpenDeepResearcher

OpenDeepResearcher is an AI-Powered Systematic Review & Research Application designed to streamline the research process through a user-friendly, multi-page interface built with Streamlit. This application guides users through the systematic review process, breaking it down into manageable steps while ensuring user involvement at each stage.

## Features

### Core Functionality
- **Multi-Page Layout**: Navigate through various stages of the research process, including Scoping, Screening, Analysis, and Reporting.
- **AI Integration**: Utilize advanced language models to assist in problem formulation, keyword generation, and data extraction.
- **Interactive Components**: Engage with interactive tables for screening articles and verifying extracted data.
- **PDF Processing**: Upload and parse PDF documents to extract relevant information for analysis.
- **Real-Time Logging**: Monitor background processes with a persistent log panel for transparency and user trust.

### Enhanced Data Collection
- **Multiple Search Methods**: Web scraping and official API integrations
- **API Support**: Direct access to academic databases through official APIs
  - **PubMed E-utilities API**: Direct access to MEDLINE database
  - **Semantic Scholar API**: AI-powered search with citation networks
  - **CORE API**: 200M+ open access research papers
- **Robust Search**: Multiple fallback strategies ensure reliable paper discovery
- **Smart Deduplication**: Automatically removes duplicate articles across sources

### Supported Data Sources
- PubMed/MEDLINE (via API and web)
- Semantic Scholar (AI-powered academic search)
- CORE (Open access research papers)
- Google Scholar (via Scholarly package)
- arXiv (preprint server)
- ResearchGate (academic network)
- DuckDuckGo Academic (general academic search)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/opendeep-researcher.git
   cd opendeep-researcher
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the application:
   - Edit `config.yaml` for API keys and settings
   - Or use the Settings page in the web interface
   - See `API_CONFIGURATION.md` for detailed API setup instructions

## Quick Start

1. **Run the application:**
   ```
   streamlit run src/app.py
   ```

2. **Configure API keys (optional but recommended):**
   - Go to Settings → API Keys tab
   - Add your CORE API key (free at https://core.ac.uk/api-keys/register)
   - Add Semantic Scholar API key (optional, get at https://www.semanticscholar.org/product/api)

3. **Start your first project:**
   - Navigate to Dashboard
   - Create a new project
   - Follow the guided workflow through Scoping → Data Collection → Screening → Analysis

## API Configuration

For enhanced data collection capabilities, configure these APIs:

### Free APIs (Recommended)
- **PubMed API**: No key required, works immediately
- **CORE API**: Free key provides 1000 requests/day
- **Semantic Scholar**: Works without key, optional key for higher limits

See `API_CONFIGURATION.md` for detailed setup instructions.

## Usage

To run the application, execute the following command in your terminal:
```
streamlit run src/app.py
```

Once the application is running, you can navigate through the various pages to manage your research projects, input your research questions, screen articles, analyze data, and generate reports.

## Directory Structure

```
opendeep-researcher
├── src
│   ├── app.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── ollama_client.py
│   │   ├── pdf_processor.py
│   │   └── data_manager.py
│   ├── pages
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   ├── settings.py
│   │   ├── scoping.py
│   │   ├── screening.py
│   │   ├── analysis.py
│   │   └── report.py
│   └── components
│       ├── __init__.py
│       ├── sidebar.py
│       └── logger.py
├── data
│   ├── projects.csv
│   └── config.json
├── requirements.txt
├── config.yaml
└── README.md
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
