# OpenDeepResearcher

OpenDeepResearcher is an AI-Powered Systematic Review & Research Application designed to streamline the research process through a user-friendly, multi-page interface built with Streamlit. This application guides users through the systematic review process, breaking it down into manageable steps while ensuring user involvement at each stage.

## Features

- **Multi-Page Layout**: Navigate through various stages of the research process, including Scoping, Screening, Analysis, and Reporting.
- **AI Integration**: Utilize advanced language models to assist in problem formulation, keyword generation, and data extraction.
- **Interactive Components**: Engage with interactive tables for screening articles and verifying extracted data.
- **PDF Processing**: Upload and parse PDF documents to extract relevant information for analysis.
- **Real-Time Logging**: Monitor background processes with a persistent log panel for transparency and user trust.

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

3. Configure the application by editing the `data/config.json` file with your Ollama API endpoint and any necessary API keys.

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