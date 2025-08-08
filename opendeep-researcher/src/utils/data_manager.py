import pandas as pd
import json
from pathlib import Path
import uuid
from typing import Dict, List, Optional

# NOTE:
#   DATA_DIR was originally defined using ``Path("../data")``.  This made the
#   location of the data directory depend on the *current working directory*
#   at import time.  When the application or tests were run from a different
#   location, data files would be created outside of the project tree (e.g. in
#   ``/workspace/data``) rather than inside the repository's ``data`` folder.
#   Such behaviour made the data manager unreliable and caused tests that rely
#   on the expected directory structure to fail.
#
#   To make the path deterministic we derive it from this module's file
#   location instead of the process's working directory.  ``__file__`` always
#   points to ``.../src/utils/data_manager.py`` so taking ``parents[2]`` gives us
#   the repository root directory (``opendeep-researcher``).  From there we join
#   the ``data`` directory.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

def ensure_data_structure():
    """Ensure the data directory structure exists."""
    DATA_DIR.mkdir(exist_ok=True)
    
    # Create projects.csv if it doesn't exist
    projects_file = DATA_DIR / "projects.csv"
    if not projects_file.exists():
        projects_df = pd.DataFrame(columns=[
            'project_id', 'title', 'description', 'created_date', 
            'status', 'research_question'
        ])
        projects_df.to_csv(projects_file, index=False)
    
    # Create config.json if it doesn't exist
    config_file = DATA_DIR / "config.json"
    if not config_file.exists():
        config = {
            "ollama_endpoint": "http://localhost:11434",
            "api_key": "",
            "screening_model": "",
            "extraction_model": "",
            "models_list": []
        }
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

def load_projects() -> pd.DataFrame:
    """Load the projects dataframe."""
    ensure_data_structure()
    projects_file = DATA_DIR / "projects.csv"
    return pd.read_csv(projects_file)

def save_projects(projects_df: pd.DataFrame):
    """Save the projects dataframe."""
    projects_file = DATA_DIR / "projects.csv"
    projects_df.to_csv(projects_file, index=False)

def create_project(title: str, description: str, research_question: str) -> str:
    """Create a new project and return the project ID."""
    project_id = str(uuid.uuid4())[:8]
    
    # Create project directory
    project_dir = DATA_DIR / project_id
    project_dir.mkdir(exist_ok=True)
    
    # Create uploads subdirectory
    uploads_dir = project_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    
    # Add to projects.csv
    projects_df = load_projects()
    new_project = {
        'project_id': project_id,
        'title': title,
        'description': description,
        'created_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'status': 'Planning',
        'research_question': research_question
    }
    projects_df = pd.concat([projects_df, pd.DataFrame([new_project])], ignore_index=True)
    save_projects(projects_df)
    
    return project_id

def get_project_dir(project_id: str) -> Path:
    """Get the project directory path."""
    return DATA_DIR / project_id

def load_config() -> Dict:
    """Load configuration from config.json."""
    ensure_data_structure()
    config_file = DATA_DIR / "config.json"
    with open(config_file, 'r') as f:
        return json.load(f)

def save_config(config: Dict):
    """Save configuration to config.json."""
    config_file = DATA_DIR / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

def load_raw_articles(project_id: str) -> pd.DataFrame:
    """Load raw articles for a project."""
    articles_file = get_project_dir(project_id) / "articles_raw.csv"
    if articles_file.exists():
        return pd.read_csv(articles_file)
    return pd.DataFrame(columns=['id', 'title', 'authors', 'abstract', 'source', 'url', 'year'])

def save_raw_articles(project_id: str, articles_df: pd.DataFrame):
    """Save raw articles for a project."""
    articles_file = get_project_dir(project_id) / "articles_raw.csv"
    articles_df.to_csv(articles_file, index=False)

def load_screened_articles(project_id: str) -> pd.DataFrame:
    """Load screened articles for a project."""
    articles_file = get_project_dir(project_id) / "articles_screened.csv"
    if articles_file.exists():
        return pd.read_csv(articles_file)
    return pd.DataFrame()

def save_screened_articles(project_id: str, articles_df: pd.DataFrame):
    """Save screened articles for a project."""
    articles_file = get_project_dir(project_id) / "articles_screened.csv"
    articles_df.to_csv(articles_file, index=False)

def load_extracted_data(project_id: str) -> pd.DataFrame:
    """Load extracted data for a project."""
    data_file = get_project_dir(project_id) / "data_extracted.csv"
    if data_file.exists():
        return pd.read_csv(data_file)
    return pd.DataFrame()

def save_extracted_data(project_id: str, article_id: str, extracted_data: Dict):
    """Save extracted data for an article."""
    data_file = get_project_dir(project_id) / "data_extracted.csv"
    
    # Load existing data
    if data_file.exists():
        df = pd.read_csv(data_file)
    else:
        df = pd.DataFrame()
    
    # Prepare new row
    new_row = {'article_id': article_id, **extracted_data}
    
    # Add or update the row
    if not df.empty and 'article_id' in df.columns:
        mask = df['article_id'] == article_id
        if mask.any():
            df.loc[mask, :] = pd.Series(new_row)
        else:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        # First row or no article_id column yet
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    df.to_csv(data_file, index=False)

def save_final_report(project_id: str, report_content: str):
    """Save the final report for a project."""
    report_file = get_project_dir(project_id) / "final_report.md"
    with open(report_file, 'w') as f:
        f.write(report_content)

def load_final_report(project_id: str) -> Optional[str]:
    """Load the final report for a project."""
    report_file = get_project_dir(project_id) / "final_report.md"
    if report_file.exists():
        with open(report_file, 'r') as f:
            return f.read()
    return None

class DataManager:
    """Legacy class for backward compatibility."""
    def __init__(self, project_id):
        self.project_id = project_id
        self.project_dir = get_project_dir(project_id)
        self.project_dir.mkdir(exist_ok=True)

    def create_project_directory(self):
        self.project_dir.mkdir(exist_ok=True)
        (self.project_dir / "uploads").mkdir(exist_ok=True)

    def read_articles_raw(self):
        return load_raw_articles(self.project_id)

    def write_articles_raw(self, data):
        save_raw_articles(self.project_id, data)

    def read_articles_screened(self):
        return load_screened_articles(self.project_id)

    def write_articles_screened(self, data):
        save_screened_articles(self.project_id, data)

    def read_data_extracted(self):
        return load_extracted_data(self.project_id)

    def write_data_extracted(self, data):
        articles_file = self.project_dir / "data_extracted.csv"
        data.to_csv(articles_file, index=False)